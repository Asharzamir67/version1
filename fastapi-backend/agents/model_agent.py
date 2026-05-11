from typing import TypedDict, Annotated, Sequence, Optional
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END, add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.runnables import RunnableConfig
from sqlalchemy.orm import Session
from sqlalchemy import func
from agents import tools
import os
import json
from datetime import datetime, date
from config import SAVED_IMAGES_DIR, DATASET_DIR
from dotenv import load_dotenv

load_dotenv(override=True)

# List of tools to be used by ToolNode
AI_TOOLS = [
    tools.get_system_stats, 
    tools.get_active_model_info, 
    tools.get_car_model_stats,
    tools.get_retraining_dataset_stats, 
    tools.get_quality_analytics, 
    tools.analyze_ng_patterns,
    tools.get_model_registry_history, 
    tools.start_model_retraining, 
    tools.log_system_observation,
    tools.get_past_observations, 
    tools.audit_system_quality, 
    tools.get_system_error_logs
]

SYSTEM_PROMPT = """
You are the Sealant Detection System's AI Supervisor. Your role is to monitor system health, audit production quality, and provide actionable insights.

MANDATORY BEHAVIOR:
1. Always call audit_system_quality() first when asked about system health, anomalies, or "how things are going".
2. If the audit reveals an NG rate > 20%, call log_system_observation() with severity=WARNING and category=MODEL_DRIFT.
3. If the NG rate exceeds 40% or if get_system_error_logs() contains "CRITICAL" or "KERNEL" errors, log a CRITICAL observation.
4. If a tool returns an empty result or "No data found", report it explicitly to the user—DO NOT invent or hallucinate data.
5. Before recommending a model retraining, always check get_model_registry_history() to ensure you aren't repeating a failed or very recent version.
6. Be professional, technical, and concise.

If the user just wants to chat or says "hi", be helpful and polite without calling any tools.
"""

SCOPE_KEYWORDS = [
    "sealant", "defect", "ng", "ok", "camera", "model", "training",
    "dataset", "quality", "inference", "yolo", "production", "corolla",
    "yaris", "system", "health", "accuracy", "retrain", "alert", "log",
    "statistics", "stats", "rate", "image", "detection", "status"
]

def is_in_scope(prompt: str) -> bool:
    """Keyword-based pre-filter to catch out-of-context questions early."""
    lowered = prompt.lower()
    # Greetings and common affirmative responses are always fine
    greetings = ["hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "summarize"]
    if any(lowered.strip().startswith(g) for g in greetings):
        return True
    return any(kw in lowered for kw in SCOPE_KEYWORDS)

# Model configuration
ADMIN_MODEL = "llama-3.3-70b-versatile"
BACKGROUND_MODEL = "llama-3.1-8b-instant"

# Define the state
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

class AgentManager:
    def __init__(self, model_name: str):
        self.llm = ChatGroq(
            model=model_name, 
            temperature=0.1,
            max_retries=1,
            timeout=30
        ).bind_tools(AI_TOOLS)
        self.app = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        def call_model(state: AgentState, config: RunnableConfig):
            # The model now uses the SYSTEM_PROMPT for better grounding
            response = self.llm.invoke(state['messages'], config=config)
            return {"messages": [response]}

        # Use the prebuilt ToolNode
        tool_node = ToolNode(AI_TOOLS)

        def should_continue(state: AgentState):
            last_message = state['messages'][-1]
            if last_message.tool_calls:
                return "tools"
            return END

        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue)
        workflow.add_edge("tools", "agent")
        
        return workflow.compile()

# Initialize specific instances for different use cases
admin_agent = AgentManager(ADMIN_MODEL)
background_agent = AgentManager(BACKGROUND_MODEL)

def get_current_model_status(db: Session, prompt: str = None, history: list = None, thread_id: str = "default_admin", use_background_model: bool = False):
    """
    Entry point for the agentic supervisor. 
    Switches between high-reasoning (70B) and low-cost (8B) models based on use case.
    """
    from models.model_registry import ModelVersion, ChatMessage
    from models.inference_result import InferenceResult
    from services.inference import get_active_model_info_from_db

    if not prompt:
        prompt = "Summarize the current system status."
    
    # 0. Fast stats for UI & Early exit usage
    _, active_name = get_active_model_info_from_db()
    try:
        db_count = db.query(func.count(InferenceResult.id)).scalar()
        image_count = 0
        if SAVED_IMAGES_DIR.exists():
            image_count = len([f for f in os.listdir(SAVED_IMAGES_DIR) if f.endswith(('.jpg', '.jpeg', '.png'))])
    except Exception as e:
        print(f"Stats Error: {str(e)}")
        db_count, image_count = 0, 0

    # 1. Scope Filter (Catch off-topic questions early)
    if not is_in_scope(prompt):
        return {
            "message": "I'm scoped to the Sealant Detection System. I can help with quality metrics, model performance, dataset health, or system status.",
            "model_name": active_name or "Unknown",
            "db_count": db_count,
            "image_count": image_count
        }

    # recursion_limit=10 gives the agent enough turns to call 3-4 diagnostic tools and reason about them
    config = {"configurable": {"thread_id": thread_id, "db": db}, "recursion_limit": 10}
    
    # 1. Save the new user message to DB
    new_msg = ChatMessage(thread_id=thread_id, role="user", content=prompt)
    db.add(new_msg)
    db.commit()

    # 2. Pull last 10 messages for context
    past_messages = db.query(ChatMessage).filter(ChatMessage.thread_id == thread_id).order_by(ChatMessage.created_at.desc()).limit(10).all()
    past_messages.reverse()
    
    # 3. Construct message list with SYSTEM_PROMPT
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for m in past_messages:
        if m.role == "user":
            messages.append(HumanMessage(content=m.content))
        else:
            messages.append(AIMessage(content=m.content))
    
    try:
        # Select the appropriate agent
        manager = background_agent if use_background_model else admin_agent
        
        final_output = manager.app.invoke({"messages": messages}, config=config)
        message = final_output["messages"][-1].content
        
        # 4. Save assistant response to DB
        ai_msg = ChatMessage(thread_id=thread_id, role="assistant", content=message)
        db.add(ai_msg)
        db.commit()
    except Exception as e:
        print(f"Agent Execution Error: {str(e)}")
        message = f"I encountered an issue while processing your request (API Limit or Loop). Details: {str(e)}"

    return {
        "message": message,
        "model_name": active_name or "Unknown",
        "db_count": db_count,
        "image_count": image_count
    }
