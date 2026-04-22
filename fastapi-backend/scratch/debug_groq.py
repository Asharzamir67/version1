import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

load_dotenv(override=True)

def test_proxy_binding():
    # Define tool without 'db' param
    @tool
    def get_system_stats():
        """Query the database and filesystem to get total records and image counts."""
        return "Success"

    try:
        # Use the same model as the main app
        llm = ChatGroq(
            model="llama-3.3-70b-versatile", 
            temperature=0,
            max_retries=0
        ).bind_tools([get_system_stats])
        
        messages = [
            SystemMessage(content="You are a helpful assistant with access to tools."),
            HumanMessage(content="how many images are there?")
        ]
        
        print("Invoking LLM...")
        response = llm.invoke(messages)
        print(f"Response Content: '{response.content}'")
        print(f"Tool Calls: {response.tool_calls}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_proxy_binding()
