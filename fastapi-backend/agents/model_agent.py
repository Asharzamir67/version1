from typing import TypedDict, Annotated, Sequence
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END, add_messages
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from models.inference_result import InferenceResult
from models.model_registry import ModelVersion
from services.inference import get_active_model_info_from_db
from services.evaluator_service import evaluate_model_performance
from services.training_service import start_retraining_background, get_training_status
import os
import json
from datetime import datetime, date
from config import SAVED_IMAGES_DIR, DATASET_DIR
from dotenv import load_dotenv

load_dotenv(override=True)

# Define the state
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

def get_current_model_status(db: Session, prompt: str = None, history: list = None):
    """Entry point for the admin route to interact with the LLM agent."""
    if not prompt:
        prompt = "Summarize the current system status."
    
    # Define Tools INSIDE to capture 'db' session via closure
    @tool
    def get_system_stats():
        """Query the database and filesystem to get total records and image counts."""
        try:
            db_count = db.query(func.count(InferenceResult.id)).scalar()
            total_images = 0
            if SAVED_IMAGES_DIR.exists():
                for root, dirs, files in os.walk(SAVED_IMAGES_DIR):
                    total_images += len([f for f in files if f.endswith(('.jpg', '.jpeg', '.png'))])
            return f"Database Records: {db_count}, Total Saved Images: {total_images}"
        except Exception as e:
            return f"Error fetching stats: {str(e)}"

    @tool
    def get_active_model_info():
        """Get information about the AI model currently 'Active' in production."""
        try:
            active = db.query(ModelVersion).filter(ModelVersion.is_active == True).first()
            if active:
                return (f"Active Model: Version {active.version_number} ({active.car_model_name})\n"
                        f"- mAP@50-95: {active.map_50_95:.4f}\n"
                        f"- Path: {active.model_path}\n"
                        f"- Created: {active.created_at.strftime('%Y-%m-%d %H:%M')}")
            return "No model is currently marked as 'Active' in the registry."
        except Exception as e:
            return f"Error fetching active model info: {str(e)}"

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

    @tool
    def get_retraining_dataset_stats():
        """Get the current state of the model retraining dataset (train vs test counts organized by car model)."""
        try:
            # DB Stats
            test_count = db.query(func.count(InferenceResult.id)).filter(InferenceResult.is_test_set == True).scalar()
            train_count = db.query(func.count(InferenceResult.id)).filter(InferenceResult.is_test_set == False).scalar()
            
            # Filesystem Stats
            fs_summary = {}
            if DATASET_DIR.exists():
                for model in os.listdir(DATASET_DIR):
                    model_path = DATASET_DIR / model
                    if model_path.is_dir():
                        fs_summary[model] = {"train": 0, "test": 0}
                        for split in ["train", "test"]:
                            split_path = os.path.join(model_path, split, "images")
                            if os.path.exists(split_path):
                                fs_summary[model][split] = len([f for f in os.listdir(split_path) if f.endswith('.jpg')])
            
            fs_str = "\n".join([f"  - {m}: {s['train']} train, {s['test']} test images" for m, s in fs_summary.items()])
            return (f"Retraining Dataset Summary:\n"
                    f"Database: {train_count} samples for training, {test_count} samples for testing.\n"
                    f"Filesystem Storage:\n{fs_str if fs_str else f'  (No model folders found in {DATASET_DIR} yet)'}")
        except Exception as e:
            return f"Error fetching dataset stats: {str(e)}"

    @tool
    def evaluate_model_on_dataset(car_model_query: str):
        """
        Evaluate the AI model's performance on the test sets of specific car models.
        Supports single model names (e.g., 'Corolla'), comma-separated lists (e.g., 'Corolla, Civic'),
        or the keyword 'all' to evaluate on the entire retraining dataset.
        Returns a detailed Performance Report and a recommendation.
        Args:
            car_model_query: The name(s) of the car model(s) or 'all'.
        """
        try:
            result = evaluate_model_performance(car_model_query)
            if not result.get("success"):
                return f"Evaluation Failed: {result.get('message', 'Unknown Error')}"
            
            return result.get("report", "No report generated.")
        except Exception as e:
            return f"Error during evaluation: {str(e)}"

    @tool
    def get_model_registry_history():
        """List all trained model versions, their performance metrics, and deployment status."""
        try:
            versions = db.query(ModelVersion).order_by(ModelVersion.version_number.desc()).all()
            if not versions:
                return "Model registry is empty."
            
            lines = ["Model Registry History:"]
            for v in versions:
                status = "[ACTIVE]" if v.is_active else "[Historical]"
                lines.append(f"{status} v{v.version_number} | {v.car_model_name} | mAP: {v.map_50_95:.4f} | Precision: {v.precision:.4f} | {v.created_at.strftime('%Y-%m-%d')}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Error fetching registry history: {str(e)}"

    @tool
    def start_model_retraining(car_model_query: str):
        """
        Initiate a background training task to create a new model version.
        Args:
            car_model_query: Car model to train on (e.g., 'Corolla' or 'all').
        """
        try:
            # Check training status first
            current = get_training_status()
            if "Training" in current:
                return f"Cannot start retraining. System status: {current}"
                
            success, msg = start_retraining_background(car_model_query)
            return msg
        except Exception as e:
            return f"Error triggering retraining: {str(e)}"

    tools = [
        get_system_stats, 
        get_active_model_info, 
        get_car_model_stats, 
        get_quality_analytics, 
        get_retraining_dataset_stats, 
        evaluate_model_on_dataset,
        get_model_registry_history,
        start_model_retraining
    ]
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
    
    # Run Agent with system context
    from langchain_core.messages import SystemMessage
    system_msg = SystemMessage(content=(
        "You are the Sealant Detection System's AI Administrator. "
        "Your goal is to provide CONCISE and RELEVANT answers to the user's questions. "
        "FOLLOW THESE RULES:\n"
        "1. ONLY call the tools necessary to answer the specific question asked.\n"
        "2. Do NOT provide a general system summary unless explicitly requested.\n"
        "3. If the user asks about retraining or evaluation, prioritize 'evaluate_model_on_dataset' and 'get_retraining_dataset_stats'.\n"
        "4. If there is not enough data for a tool to work, simply state that and explain what is missing, without dumping unrelated statistics.\n"
        "5. Use 'mAP' (mean Average Precision) to suggest retraining when scores are below 0.75."
    ))
    # Convert history list (dicts) to LangChain messages
    history_messages = []
    if history:
        # Only take the last 10 messages to avoid token limit issues
        for msg in history[-10:]:
            role = msg.get('role')
            content = msg.get('content') or ""
            if role == 'user':
                history_messages.append(HumanMessage(content=content))
            elif role == 'assistant':
                history_messages.append(AIMessage(content=content))
    
    initial_state = {"messages": [system_msg] + history_messages + [HumanMessage(content=prompt)]}
    try:
        final_output = app.invoke(initial_state)
        last_msg = final_output["messages"][-1]
        message = last_msg.content
    except Exception as e:
        print(f"Agent Execution Error: {str(e)}")
        message = f"Agent Error: {str(e)}"
    
    # Extract stats for UI cards (static refresh)
    active_path, active_name = get_active_model_info_from_db()
    try:
        db_count = db.query(func.count(InferenceResult.id)).scalar()
        image_count = 0
        if SAVED_IMAGES_DIR.exists():
            for root, dirs, files in os.walk(SAVED_IMAGES_DIR):
                image_count += len([f for f in files if f.endswith(('.jpg', '.jpeg', '.png'))])
    except:
        db_count, image_count = 0, 0

    return {
        "message": message,
        "model_name": active_name or "Unknown",
        "db_count": db_count,
        "image_count": image_count
    }
