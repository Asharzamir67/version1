# Agentic Supervisor Architecture

This document describes the stateful orchestration of the AI Supervisor using LangGraph.

## StateGraph Visualization

![Agentic Supervisor Technical Schematic](system_architecture.svg)

```mermaid
graph TD
    %% Global Lifecycle
    Start((Hourly Cron)) -->|Loop| Session[SessionLocal created]
    Session --> Input[Human/Autonomous Prompt]
    
    %% The LangGraph Agent
    subgraph StateGraph [LangGraph State Machine]
        Input --> AgentNode["Node: 'agent' (LLM)"]
        AgentNode --> Condition{should_continue?}
        
        Condition -->|tool_calls| ToolsNode["Node: 'tools' (Dispatcher)"]
        Condition -->|__end__| Output[Final Message]
        
        ToolsNode -->|Tool Results| AgentNode
    end

    %% Tools Layer
    subgraph ExternalTools [System Tools Layer]
        ToolsNode -.-> T1[audit_system_quality]
        ToolsNode -.-> T2[analyze_ng_patterns]
        ToolsNode -.-> T3[get_system_error_logs]
        ToolsNode -.-> T4[log_system_observation]
    end

    %% Persistence & UX
    Output --> UI[Admin Dashboard / AI Insights]
    T4 --> DB[(PostgreSQL)]
    T4 --> Notify[NotificationService]
```

## Logic Breakdown

### 1. The 'agent' Node
The LLM (Llama 3.1 8B) is invoked with the current `AgentState` (message history). It decides if the current task can be answered directly or if it needs to query the system using a tool.

### 2. The 'tools' Node (Manual Dispatcher)
This is the **Security Firewall**. The LLM never touches the database directly. It sends a "Tool Call" request. Our dispatcher:
1.  Receives the request.
2.  Maps the request name to a Python function in `tools.py`.
3.  Injects the **Active Database Session**.
4.  Returns the raw data to the Agent.

### 3. Conditional Edge: `should_continue`
A simple logic gate:
*   If the LLM's last response contains `tool_calls`, go to the `tools` node.
*   If the LLM has finished its investigation and provided a summary, go to `END`.

### 4. Background Loop
The `autonomous_supervisor_loop` in `main.py` runs as an asynchronous task. It ensures that even if no human is logged in, the agent is performing "System Audits" every hour and logging `SystemObservations` to the database.
