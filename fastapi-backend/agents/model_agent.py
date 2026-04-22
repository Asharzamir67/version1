from typing import TypedDict, Annotated, Sequence, Optional
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END, add_messages
# Removed MemorySaver to prevent duplication with frontend-managed history
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

# Define the state
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

class AgentManager:
    def __init__(self, model_name: str = "llama-3.3-70b-versatile"):
        self._setup_ai_tools()
        # Bind the simple tool schemas to the LLM
        # Using a slightly higher temperature to avoid repetitive loops
        # Added timeout and max_retries=0 to prevent the backend from hanging on rate limits
        self.llm = ChatGroq(
            model=model_name, 
            temperature=0.1, # Lower temperature for more stability in tool calling
            max_retries=1,
            timeout=30
        ).bind_tools(self.ai_tools)
        # We'll build the graph without a checkpointer for now because the frontend manages history
        self.app = self._build_graph()

    def _setup_ai_tools(self):
        """
        Define lightweight tool schemas for the LLM. 
        """
        @tool
        def get_system_stats():
            """Query the database and filesystem to get total records and image counts."""
            return "Fetching stats..."

        @tool
        def get_active_model_info():
            """Get information about the AI model currently 'Active' in production."""
            return "Fetching model info..."

        @tool
        def get_car_model_stats(model_name: str, only_today: bool = False):
            """Count how many cars of a specific model type were processed."""
            return f"Counting for {model_name}..."

        @tool
        def get_retraining_dataset_stats():
            """Get the current state of the model retraining dataset (train vs test counts organized by car model)."""
            return "Fetching dataset stats..."

        @tool
        def get_quality_analytics():
            """Calculate the overall OK/NG classification rate based on image statuses."""
            return "Calculating quality metrics..."

        @tool
        def analyze_ng_patterns(car_model: Optional[str] = None):
            """Advanced Root Cause Analysis: Identifies which camera is producing the most NG results."""
            return "Performing RCA..."

        @tool
        def get_model_registry_history():
            """List all trained model versions, performance metrics, and deployment status."""
            return "Fetching registry history..."

        @tool
        def start_model_retraining(car_model_query: str):
            """Initiate a background training task for a new model version."""
            return f"Starting training for {car_model_query}..."

        @tool
        def log_system_observation(severity: str, category: str, observation: str):
            """Log a persistent observation (INFO/WARNING/CRITICAL) about (MODEL_DRIFT/HARDWARE/DATASET)."""
            return "Logging observation..."

        @tool
        def get_past_observations(limit: int = 5):
            """Retrieve historical system observations."""
            return f"Fetching last {limit} observations..."

        @tool
        def audit_system_quality():
            """Perform a time-series audit to find sudden spikes in NG results."""
            return "Auditing quality trends..."

        @tool
        def get_system_error_logs(lines: int = 20):
            """Read the latest entries from alerts.log and kernel.errors.txt."""
            return f"Reading last {lines} lines of logs..."

        self.ai_tools = [
            get_system_stats, get_active_model_info, get_car_model_stats,
            get_retraining_dataset_stats, get_quality_analytics, analyze_ng_patterns,
            get_model_registry_history, start_model_retraining, log_system_observation,
            get_past_observations, audit_system_quality, get_system_error_logs
        ]

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        def call_model(state: AgentState, config: RunnableConfig):
            # Ensure the model knows about previous tool outputs to stop loops
            response = self.llm.invoke(state['messages'], config=config)
            return {"messages": [response]}

        def execute_tools(state: AgentState, config: RunnableConfig):
            last_message = state['messages'][-1]
            tool_outputs = []
            db = config.get("configurable", {}).get("db")
            
            for tool_call in last_message.tool_calls:
                name = tool_call["name"]
                args = tool_call["args"]
                print(f"--- [AGENT] Executing Tool: {name} with args: {args} ---")
                
                try:
                    # Map the tool name to the actual implementation function in the tools module
                    tool_func = getattr(tools, name, None)
                    
                    if tool_func:
                        if name in ["get_system_stats", "get_active_model_info", "get_retraining_dataset_stats", "get_quality_analytics", "get_model_registry_history", "audit_system_quality"]:
                            output = tool_func(db)
                        elif name in ["get_car_model_stats", "analyze_ng_patterns", "log_system_observation", "get_past_observations"]:
                            output = tool_func(db, **args)
                        else:
                            # Tools that don't require a DB session
                            output = tool_func(**args)
                    else:
                        output = f"Error: Implementation for tool '{name}' not found in tools module."
                except Exception as e:
                    output = f"Error executing {name}: {str(e)}"
                
                tool_outputs.append(ToolMessage(
                    content=str(output),
                    tool_call_id=tool_call["id"]
                ))
            return {"messages": tool_outputs}

        def should_continue(state: AgentState):
            last_message = state['messages'][-1]
            # Limit the number of tool calls to prevent infinite loops
            # Note: recursion_limit in invoke handles this better globally
            if last_message.tool_calls:
                return "tools"
            return END

        workflow.add_node("agent", call_model)
        workflow.add_node("tools", execute_tools)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue)
        workflow.add_edge("tools", "agent")
        
        return workflow.compile() # Removed checkpointer

# Initialize a global manager instance
agent_manager = AgentManager()

def get_current_model_status(db: Session, prompt: str = None, history: list = None, thread_id: str = "default_admin"):
    """
    Entry point for the agentic supervisor. 
    Now stateless to prevent history duplication issues.
    """
    from models.model_registry import ModelVersion, ChatMessage
    from models.inference_result import InferenceResult
    from services.inference import get_active_model_info_from_db

    if not prompt:
        prompt = "Summarize the current system status."
    
    # recursion_limit=10 gives the agent enough turns to call 3-4 diagnostic tools and reason about them
    config = {"configurable": {"thread_id": thread_id, "db": db}, "recursion_limit": 10}
    
    system_msg = SystemMessage(content=(
        "You are the Sealant Detection System's AI Supervisor. "
        "Your role is to monitor system health, audit production quality, and provide actionable insights.\n"
        "You have access to several diagnostic tools. Use them to answer user questions about the system state, "
        "production statistics, or dataset health. "
        "When you use a tool, wait for the result and then explain it to the user in a friendly, professional way.\n\n"
        "If the user just wants to chat or says 'hi', be helpful and polite without calling any tools."
    ))

    # 1. Save the new user message to DB
    if prompt:
        new_msg = ChatMessage(thread_id=thread_id, role="user", content=prompt)
        db.add(new_msg)
        db.commit()

    # 2. Pull last 10 messages for this thread_id from DB for context
    past_messages = db.query(ChatMessage).filter(ChatMessage.thread_id == thread_id).order_by(ChatMessage.created_at.desc()).limit(10).all()
    # Reverse to get chronological order
    past_messages.reverse()
    
    # 3. Construct message list for LLM
    messages = [system_msg]
    for m in past_messages:
        if m.role == "user":
            messages.append(HumanMessage(content=m.content))
        else:
            messages.append(AIMessage(content=m.content))
    
    try:
        final_output = agent_manager.app.invoke({"messages": messages}, config=config)
        message = final_output["messages"][-1].content
        
        # 4. Save assistant response to DB
        ai_msg = ChatMessage(thread_id=thread_id, role="assistant", content=message)
        db.add(ai_msg)
        db.commit()
    except Exception as e:
        print(f"Agent Execution Error: {str(e)}")
        message = f"I encountered an issue while processing your request (API Limit or Loop). Details: {str(e)}"

    # Fast stats for UI
    _, active_name = get_active_model_info_from_db()
    try:
        db_count = db.query(func.count(InferenceResult.id)).scalar()
        # Non-recursive count for speed
        image_count = 0
        if SAVED_IMAGES_DIR.exists():
            image_count = len([f for f in os.listdir(SAVED_IMAGES_DIR) if f.endswith(('.jpg', '.jpeg', '.png'))])
    except Exception as e:
        print(f"Stats Error: {str(e)}")
        db_count, image_count = 0, 0
    
    return {
        "message": message,
        "model_name": active_name or "Unknown",
        "db_count": db_count,
        "image_count": image_count
    }
