from typing import TypedDict, Annotated, Sequence, Optional
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END, add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig
from sqlalchemy.orm import Session
from agents import tools
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Define the state
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

class AgentManager:
    def __init__(self, model_name: str = "llama-3.1-8b-instant"):
        self._setup_ai_tools()
        # Bind the simple tool schemas to the LLM
        self.llm = ChatGroq(model=model_name, temperature=0.1).bind_tools(self.ai_tools)
        self.memory = MemorySaver()
        self.app = self._build_graph()

    def _setup_ai_tools(self):
        """
        Define lightweight tool schemas for the LLM. 
        These are standard functions that LangChain can inspect easily.
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
            """Initiate a background training task for a new model version (e.g., 'Corolla' or 'all')."""
            return f"Starting training for {car_model_query}..."

        @tool
        def log_system_observation(severity: str, category: str, observation: str):
            """Log a persistent observation (INFO/WARNING/CRITICAL) about (MODEL_DRIFT/HARDWARE/DATASET)."""
            return "Logging observation..."

        @tool
        def get_past_observations(limit: int = 5):
            """Retrieve historical system observations. The limit argument MUST be a JSON integer."""
            return f"Fetching last {limit} observations..."

        @tool
        def audit_system_quality():
            """Perform a time-series audit to find sudden spikes in NG results (Last hour vs 24h)."""
            return "Auditing quality trends..."

        @tool
        def get_system_error_logs(lines: int = 20):
            """Read the latest entries from alerts.log and kernel.errors.txt to diagnose failures."""
            return f"Reading last {lines} lines of logs..."

        self.ai_tools = [
            get_system_stats, get_active_model_info, get_car_model_stats,
            get_quality_analytics, analyze_ng_patterns, get_model_registry_history,
            start_model_retraining, log_system_observation, get_past_observations,
            audit_system_quality, get_system_error_logs
        ]

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        def call_model(state: AgentState, config: RunnableConfig):
            # The LLM only sees the messages, not the DB session
            response = self.llm.invoke(state['messages'], config=config)
            return {"messages": [response]}

        def execute_tools(state: AgentState, config: RunnableConfig):
            last_message = state['messages'][-1]
            tool_outputs = []
            db = config.get("configurable", {}).get("db")
            
            for tool_call in last_message.tool_calls:
                name = tool_call["name"]
                args = tool_call["args"]
                
                # Manual Dispatcher: Map AI calls to real functions in tools.py
                try:
                    if name == "get_system_stats":
                        output = tools.get_system_stats(db)
                    elif name == "get_active_model_info":
                        output = tools.get_active_model_info(db)
                    elif name == "get_car_model_stats":
                        output = tools.get_car_model_stats(db, **args)
                    elif name == "get_quality_analytics":
                        output = tools.get_quality_analytics(db)
                    elif name == "analyze_ng_patterns":
                        output = tools.analyze_ng_patterns(db, **args)
                    elif name == "get_model_registry_history":
                        output = tools.get_model_registry_history(db)
                    elif name == "start_model_retraining":
                        output = tools.start_model_retraining(**args)
                    elif name == "log_system_observation":
                        output = tools.log_system_observation(db, **args)
                    elif name == "get_past_observations":
                        limit_val = args.get("limit", 5)
                        if isinstance(limit_val, str):
                            limit_val = int(limit_val)
                        output = tools.get_past_observations(db, limit=limit_val)
                    elif name == "audit_system_quality":
                        output = tools.audit_system_quality(db)
                    elif name == "get_system_error_logs":
                        output = tools.get_system_error_logs(**args)
                    else:
                        output = f"Error: Tool '{name}' not found in dispatcher."
                except Exception as e:
                    output = f"Error executing {name}: {str(e)}"
                
                tool_outputs.append(ToolMessage(
                    content=str(output),
                    tool_call_id=tool_call["id"]
                ))
            return {"messages": tool_outputs}

        def should_continue(state: AgentState):
            last_message = state['messages'][-1]
            if last_message.tool_calls:
                return "tools"
            return END

        workflow.add_node("agent", call_model)
        workflow.add_node("tools", execute_tools)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue)
        workflow.add_edge("tools", "agent")
        
        return workflow.compile(checkpointer=self.memory)

# Initialize a global manager instance
agent_manager = AgentManager()

def get_current_model_status(db: Session, prompt: str = None, thread_id: str = "default_admin"):
    """
    Entry point for the agentic supervisor using a stateful LangGraph.
    """
    if not prompt:
        prompt = "Summarize the current system status and check for any anomalies."
    
    config = {"configurable": {"thread_id": thread_id, "db": db}}
    
    # Prepend system instruction if this is a new conversation context
    system_msg = SystemMessage(content=(
        "You are the Sealant Detection System's AI Supervisor. "
        "Your mission is to ensure production quality through proactive monitoring.\n\n"
        "FACILITIES:\n"
        "1. AUDIT: Use 'audit_system_quality' first to find spikes or trends.\n"
        "2. RCA: If you see defects, use 'analyze_ng_patterns' and 'get_system_error_logs' to find the cause.\n"
        "3. LOGGING: Use 'log_system_observation' to save findings permanently.\n"
        "4. HISTORY: Use 'get_past_observations' to see what happened earlier.\n"
    ))

    inputs = {
        "messages": [system_msg, HumanMessage(content=prompt)]
    }
    
    try:
        final_output = agent_manager.app.invoke(inputs, config=config)
        message = final_output["messages"][-1].content
    except Exception as e:
        message = f"Agent Error: {str(e)}"

    # Provide UI metadata
    from services.inference import get_active_model_info_from_db
    _, active_name = get_active_model_info_from_db()
    
    return {
        "message": message,
        "model_name": active_name or "Unknown",
        "db_count": 0,
        "image_count": 0
    }
