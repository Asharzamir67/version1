import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { authAPI } from '../services/api'
import './AdminDashboard.css'
import logo from '../components/logo.png'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from '../components/Charts'
import AIInsights from '../components/AIInsights'

const AdminDashboard = ({ user, onLogout }) => {
  const navigate = useNavigate()
  const [modelStatus, setModelStatus] = useState(null)
  const [chatHistory, setChatHistory] = useState([])
  const [prompt, setPrompt] = useState("")
  const [isAsking, setIsAsking] = useState(false)
  const [dailyStats, setDailyStats] = useState([])
  const [datasetStats, setDatasetStats] = useState([])
  const [modelRegistry, setModelRegistry] = useState([])
  const [systemObservations, setSystemObservations] = useState([])
  const [activeTab, setActiveTab] = useState('analytics') // 'analytics', 'dataset', 'registry', 'insights', 'retraining'
  const [loadingData, setLoadingData] = useState(true)
  const [trainingStatus, setTrainingStatus] = useState({ status: 'Idle', stage: 'Idle', progress: 0, message: 'Ready' })
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [chatHistory, isAsking])

  useEffect(() => {
    if (!user || user.role !== 'admin') {
      navigate('/')
    } else {
      loadChatHistory()
    }
  }, [user])

  useEffect(() => {
    if (user && user.role === 'admin') {
      loadTabData()
    }
  }, [user, activeTab])

  // Real-time training status via WebSockets
  useEffect(() => {
    if (!user || user.role !== 'admin') return;

    // Connect to WebSocket for real-time progress updates
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = 'localhost:8000'; // Ensure this matches your backend host
    const wsUrl = `${protocol}//${host}/ws/training-status`;
    
    let ws;
    let reconnectTimer;

    const connect = () => {
      console.log("--- [DASHBOARD] Connecting to WebSocket ---");
      ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setTrainingStatus(prev => {
          if (data.status === 'Idle' && prev.status === 'Busy') {
            if (activeTab === 'registry') loadTabData();
          }
          return data;
        });
      };

      ws.onclose = () => {
        console.log("--- [DASHBOARD] WebSocket Disconnected. Reconnecting... ---");
        reconnectTimer = setTimeout(connect, 5000);
      };

      ws.onerror = (err) => {
        console.error("--- [DASHBOARD] WebSocket Error ---", err);
        ws.close();
      };
    };

    connect();

    return () => {
      if (ws) ws.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, [user]);

  const loadChatHistory = async () => {
    try {
      const res = await authAPI.getChatHistory()
      if (res.data && res.data.length > 0) {
        setChatHistory(res.data)
      } else {
        setChatHistory([{ role: 'assistant', content: "Hello Admin! I'm your AI System Assistant. How can I help you today?" }])
      }
    } catch (error) {
      console.error("Failed to load chat history:", error)
      setChatHistory([{ role: 'assistant', content: "Hello Admin! I'm your AI System Assistant. How can I help you today?" }])
    }
  }

  const fetchModelStatus = async (customPrompt = null) => {
    setIsAsking(true);
    const currentHistory = [...chatHistory];

    if (customPrompt) {
      setChatHistory(prev => [...prev, { role: 'user', content: customPrompt }]);
    }

    try {
      // Note: Backend uses the token to identify the admin (thread_id)
      const response = await authAPI.getModelStatus(customPrompt, currentHistory);
      setModelStatus(response.data);
      if (customPrompt) {
        setChatHistory(prev => [...prev, { role: 'assistant', content: response.data.message }]);
        setPrompt("");
      } else {
        // First load or full refresh - if we get here from System Refresh, we overwrite
        setChatHistory([{ role: 'assistant', content: response.data.message }]);
      }
    } catch (error) {
      console.error("Failed to fetch model status:", error);
      const errorMsg = "Error: Could not reach the AI agent. Please check your API key.";
      if (customPrompt) {
        setChatHistory(prev => [...prev, { role: 'assistant', content: errorMsg }]);
      } else {
        setChatHistory([{ role: 'assistant', content: errorMsg }]);
      }
    } finally {
      setIsAsking(false);
    }
  };

  const loadTabData = async () => {
    setLoadingData(true)
    try {
      if (activeTab === 'analytics') {
        const res = await authAPI.getDailyStats()
        setDailyStats(res.data)
      } else if (activeTab === 'dataset') {
        const res = await authAPI.getDatasetStats()
        setDatasetStats(res.data)
      } else if (activeTab === 'registry') {
        const res = await authAPI.getModelRegistry()
        setModelRegistry(res.data)
      } else if (activeTab === 'insights') {
        const res = await authAPI.getSystemObservations()
        setSystemObservations(res.data.observations)
      }
    } catch (error) {
      console.error(`Failed to fetch ${activeTab} data:`, error)
    } finally {
      setLoadingData(false)
    }
  }


  const handleLogout = async () => {
    if (onLogout) await onLogout()
    navigate('/')
  }

  return (
    <div className="admin-dashboard">
      <header className="dashboard-header">
        <div className="header-left">
          <img src={logo} alt="Sealant Logo" className="dashboard-logo" />
          <div className="header-content">
            <h1>Admin Control Center</h1>
            <p className="user-info">Logged in as: {user?.username}</p>
          </div>
        </div>
        <button className="logout-button" onClick={handleLogout}>Log Out</button>
      </header>

      <main className="dashboard-layout">
        {/* Left Section (70%) */}
        <div className="dashboard-left-panel">
          <div className="admin-card tabs-card">
            <div className="tabs-header">
              <button 
                className={`tab-btn ${activeTab === 'analytics' ? 'active' : ''}`}
                onClick={() => setActiveTab('analytics')}
              >
                Inference Analytics
              </button>
              <button 
                className={`tab-btn ${activeTab === 'retraining' ? 'active' : ''}`}
                onClick={() => setActiveTab('retraining')}
              >
                Model Retraining {trainingStatus.status === 'Busy' && <span className="pulse-dot"></span>}
              </button>
              <button 
                className={`tab-btn ${activeTab === 'dataset' ? 'active' : ''}`}
                onClick={() => setActiveTab('dataset')}
              >
                Dataset Sizes
              </button>
              <button 
                className={`tab-btn ${activeTab === 'registry' ? 'active' : ''}`}
                onClick={() => setActiveTab('registry')}
              >
                Model Registry
              </button>
              <button 
                className={`tab-btn ${activeTab === 'insights' ? 'active' : ''}`}
                onClick={() => setActiveTab('insights')}
              >
                AI Insights
              </button>
            </div>

            <div className="tab-content">
              {loadingData ? (
                <div className="loading-placeholder">Loading {activeTab}...</div>
              ) : (
                <>
                  {activeTab === 'analytics' && (
                    <div className="analytics-tab">
                      <h3>Daily Production Analytics (OK vs NG)</h3>
                      <div className="chart-container">
                        <ResponsiveContainer width="100%" height={350}>
                          <BarChart data={dailyStats} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} />
                            <XAxis dataKey="date" axisLine={false} tickLine={false} />
                            <YAxis axisLine={false} tickLine={false} />
                            <Tooltip
                              contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                              cursor={{ fill: '#f1f5f9' }}
                            />
                            <Legend iconType="circle" />
                            <Bar dataKey="ok" name="OK Results" fill="#10b981" radius={[4, 4, 0, 0]} />
                            <Bar dataKey="ng" name="NG Results" fill="#ef4444" radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  )}

                  {activeTab === 'dataset' && (
                    <div className="dataset-tab">
                      <h3>Dataset Distribution Per Model</h3>
                      <div className="dataset-grid">
                        {datasetStats.map((stat, i) => (
                          <div key={i} className="dataset-item">
                            <div className="model-label">{stat.model}</div>
                            <div className="stats-row">
                              <div className="stat-pill train">
                                <span className="label">Train</span>
                                <span className="value">{stat.train}</span>
                              </div>
                              <div className="stat-pill test">
                                <span className="label">Test</span>
                                <span className="value">{stat.test}</span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {activeTab === 'registry' && (
                    <div className="registry-tab">
                      <h3>Model Version History</h3>
                      <div className="table-responsive">
                        <table className="registry-table">
                          <thead>
                            <tr>
                              <th>Version</th>
                              <th>Car Model</th>
                              <th>mAP@50-95</th>
                              <th>Training Data</th>
                              <th>Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            {modelRegistry.map((model, i) => (
                              <tr key={i} className={model.is_active ? 'active-row' : ''}>
                                <td className="bold">v{model.version}</td>
                                <td>{model.car_model}</td>
                                <td>{(model.map * 100).toFixed(1)}%</td>
                                <td>{model.training_data}</td>
                                <td>
                                  <span className={`status-badge ${model.is_active ? 'active' : 'inactive'}`}>
                                    {model.is_active ? 'Active' : 'Historical'}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {activeTab === 'insights' && (
                    <div className="insights-tab">
                      <AIInsights observations={systemObservations} />
                    </div>
                  )}

                  {activeTab === 'retraining' && (
                    <div className="retraining-tab">
                      <div className="tab-header-flex">
                        <h3>AI Model Retraining Progress</h3>
                        {trainingStatus.status === 'Busy' && <div className="live-badge">LIVE</div>}
                      </div>
                      
                      <div className="retraining-status-container">
                        <div className="status-grid">
                          <div className="status-card">
                            <span className="label">Current Status</span>
                            <div className={`value bold ${trainingStatus.status.toLowerCase()}`}>
                              {trainingStatus.status}
                            </div>
                          </div>
                          <div className="status-card">
                            <span className="label">Current Stage</span>
                            <div className="value bold">{trainingStatus.stage}</div>
                          </div>
                          <div className="status-card">
                            <span className="label">Car Model</span>
                            <div className="value">{trainingStatus.car_model || 'None'}</div>
                          </div>
                        </div>
                        
                        <div className="progress-section">
                          <div className="progress-info-row">
                            <span>Processing Completion</span>
                            <span className="bold">{trainingStatus.progress}%</span>
                          </div>
                          <div className="progress-bar-container">
                            <div 
                              className={`progress-bar-fill ${trainingStatus.status === 'Busy' ? 'animating' : ''}`} 
                              style={{ width: `${trainingStatus.progress}%` }}
                            ></div>
                          </div>
                          {trainingStatus.current_epoch > 0 && (
                            <div className="epoch-indicator">
                              Epoch {trainingStatus.current_epoch} of {trainingStatus.total_epochs}
                            </div>
                          )}
                        </div>

                        <div className="status-message-box">
                          <div className="msg-icon">ℹ️</div>
                          <div className="msg-content">
                            <p>{trainingStatus.message}</p>
                            {trainingStatus.last_update && (
                              <small>Last updated at: {trainingStatus.last_update}</small>
                            )}
                          </div>
                        </div>

                        <div className="workflow-timeline">
                          <h4>Training Workflow</h4>
                          <div className="timeline-items">
                            <div className={`timeline-item ${trainingStatus.stage === 'Preparing' ? 'active' : ''} ${trainingStatus.progress > 20 ? 'completed' : ''}`}>
                              <div className="dot"></div>
                              <div className="content">
                                <h5>1. Dataset Preparation</h5>
                                <p>Scanning folders, compiling images, and generating YOLO configuration.</p>
                              </div>
                            </div>
                            <div className={`timeline-item ${trainingStatus.stage === 'Training' ? 'active' : ''} ${trainingStatus.progress > 80 ? 'completed' : ''}`}>
                              <div className="dot"></div>
                              <div className="content">
                                <h5>2. Neural Network Training</h5>
                                <p>Fine-tuning the model weights. Most resource-intensive phase.</p>
                              </div>
                            </div>
                            <div className={`timeline-item ${trainingStatus.stage === 'Evaluating' ? 'active' : ''} ${trainingStatus.progress === 100 ? 'completed' : ''}`}>
                              <div className="dot"></div>
                              <div className="content">
                                <h5>3. Evaluation & Promotion</h5>
                                <p>Comparing Challenger vs Champion performance for automatic promotion.</p>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

        </div>

        {/* Right Section (30%) */}
        <div className="dashboard-right-panel">
          <div className="admin-card agent-sidebar">
            <h3>AI System Agent</h3>
            <div className="agent-display" ref={scrollRef}>
              {chatHistory.length === 0 ? (
                <p className="agent-msg-sidebar italic">Ready for your command.</p>
              ) : (
                chatHistory.map((msg, idx) => (
                  <div key={idx} className={`chat-bubble ${msg.role}`}>
                    <div className="bubble-header">{msg.role === 'user' ? 'You' : 'Agent'}</div>
                    <div className="bubble-content">{msg.content}</div>
                  </div>
                ))
              )}
              {isAsking && (
                <div className="chat-bubble assistant processing">
                   <div className="bubble-header">Agent</div>
                   <div className="bubble-content">Thinking...</div>
                </div>
              )}
            </div>

            <div className="agent-chat-controls">
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Ask agent..."
                onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), fetchModelStatus(prompt))}
                disabled={isAsking}
              />
              <button
                className="ask-btn"
                onClick={() => fetchModelStatus(prompt)}
                disabled={isAsking || !prompt.trim()}
              >
                {isAsking ? "..." : "Send"}
              </button>
            </div>
            <button className="refresh-link" onClick={() => fetchModelStatus()}>System Refresh</button>
          </div>
        </div>
      </main>
    </div>
  )
}

export default AdminDashboard
