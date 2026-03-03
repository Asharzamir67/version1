from typing import TypedDict, Annotated, Sequence
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END, add_messages
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from models.inference_result import InferenceResult
from services.inference import ACTIVE_MODEL_NAME
import os
import json
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv(override=True)

# Define the state
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

def get_current_model_status(db: Session, prompt: str = "Summarize the current system status."):
    """Entry point for the admin route to interact with the LLM agent."""
    
    # Define Tools INSIDE to capture 'db' session via closure
    @tool
    def get_system_stats():
        """Query the database and filesystem to get total records and image counts."""
        try:
            db_count = db.query(func.count(InferenceResult.id)).scalar()
            save_dir = "saved_images"
            total_images = 0
            if os.path.exists(save_dir):
                for root, dirs, files in os.walk(save_dir):
                    total_images += len([f for f in files if f.endswith(('.jpg', '.jpeg', '.png'))])
            return f"Database Records: {db_count}, Total Saved Images: {total_images}"
        except Exception as e:
            return f"Error fetching stats: {str(e)}"

    @tool
    def get_active_model_info():
        """Get the name of the AI model currently being used for inference."""
        return f"The currently active AI model is: {ACTIVE_MODEL_NAME}"

    @tool
    def get_car_model_stats(model_name: str, only_today: bool = False):
        """
        Count how many cars of a specific model type were processed.
        Args:
            model_name: The name or part of the name of the car model (e.g., 'Toyoto', 'Corolla').
            only_today: If True, only count cars processed today.
        """
        try:
            query = db.query(func.count(InferenceResult.id)).filter(
                InferenceResult.car_model.ilike(f"%{model_name}%")
            )
            if only_today:
                today = date.today()
                query = query.filter(func.date(InferenceResult.input_time) == today)
            
            count = query.scalar()
            time_str = "today" if only_today else "in total"
            return f"Found {count} entries for car model '{model_name}' {time_str}."
        except Exception as e:
            return f"Error fetching car model stats: {str(e)}"

    @tool
    def get_quality_analytics():
        """Calculate the overall OK/NG classification rate based on image statuses."""
        try:
            results = db.query(
                InferenceResult.image1_status,
                InferenceResult.image2_status,
                InferenceResult.image3_status,
                InferenceResult.image4_status
            ).all()
            
            if not results:
                return "No inference data available to calculate quality stats."
                
            total_checks = len(results) * 4
            ok_count = 0
            for row in results:
                ok_count += sum(1 for status in row if status and status.lower() == 'ok')
            
            ng_count = total_checks - ok_count
            ok_rate = (ok_count / total_checks) * 100
            
            return (f"Quality Analytics: Out of {total_checks} image checks, "
                    f"{ok_count} were OK ({ok_rate:.1f}%) and {ng_count} were NG.")
        except Exception as e:
            return f"Error calculating quality stats: {str(e)}"

    tools = [get_system_stats, get_active_model_info, get_car_model_stats, get_quality_analytics]
    tools_dict = {t.name: t for t in tools}
    
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1).bind_tools(tools)

    def call_model(state: AgentState):
        print("--- CALLING MODEL ---")
        try:
            response = llm.invoke(state['messages'])
            print(f"--- MODEL RESPONSE (Tool calls: {len(response.tool_calls)}) ---")
            return {"messages": [response]}
        except Exception as e:
            print(f"--- LLM ERROR: {str(e)} ---")
            raise e

    def execute_tools(state: AgentState):
        print("--- EXECUTING TOOLS ---")
        last_message = state['messages'][-1]
        tool_outputs = []
        for tool_call in last_message.tool_calls:
            print(f"--- INVOKING TOOL: {tool_call['name']} ---")
            tool_obj = tools_dict[tool_call["name"]]
            output = tool_obj.invoke(tool_call["args"])
            print(f"--- TOOL OUTPUT: {str(output)[:100]}... ---")
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

    # Build Graph
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", execute_tools)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")
    
    app = workflow.compile()
    
    # Run Agent
    initial_state = {"messages": [HumanMessage(content=prompt)]}
    try:
        final_output = app.invoke(initial_state)
        last_msg = final_output["messages"][-1]
        message = last_msg.content
    except Exception as e:
        print(f"Agent Execution Error: {str(e)}")
        message = f"Agent Error: {str(e)}"
    
    # Extract stats for UI cards (static refresh)
    try:
        db_count = db.query(func.count(InferenceResult.id)).scalar()
        save_dir = "saved_images"
        image_count = 0
        if os.path.exists(save_dir):
            for root, dirs, files in os.walk(save_dir):
                image_count += len([f for f in files if f.endswith(('.jpg', '.jpeg', '.png'))])
    except:
        db_count, image_count = 0, 0

    return {
        "message": message,
        "model_name": ACTIVE_MODEL_NAME,
        "db_count": db_count,
        "image_count": image_count
    }
