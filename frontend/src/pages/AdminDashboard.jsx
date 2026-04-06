import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { authAPI } from '../services/api'
import './AdminDashboard.css'
import logo from '../components/logo.png'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from '../components/Charts'

const AdminDashboard = ({ user, onLogout }) => {
  const navigate = useNavigate()
  const [modelStatus, setModelStatus] = useState(null)
  const [prompt, setPrompt] = useState("")
  const [isAsking, setIsAsking] = useState(false)
  const [dailyStats, setDailyStats] = useState([])
  const [loadingStats, setLoadingStats] = useState(true)

  useEffect(() => {
    if (!user || user.role !== 'admin') {
      navigate('/')
    } else {
      fetchModelStatus()
      fetchDailyStats()
    }
  }, [user, navigate])

  const fetchModelStatus = async (customPrompt = null) => {
    setIsAsking(true);
    try {
      const response = await authAPI.getModelStatus(customPrompt);
      setModelStatus(response.data);
      if (customPrompt) setPrompt("");
    } catch (error) {
      console.error("Failed to fetch model status:", error);
      setModelStatus(prev => ({
        ...prev,
        message: "Error: Could not reach the AI agent. Please check your API key."
      }));
    } finally {
      setIsAsking(false);
    }
  };

  const fetchDailyStats = async () => {
    setLoadingStats(true)
    try {
      const response = await authAPI.getDailyStats()
      setDailyStats(response.data)
    } catch (error) {
      console.error("Failed to fetch daily stats:", error)
    } finally {
      setLoadingStats(false)
    }
  }

  const handleOpenFolder = async () => {
    try {
      await authAPI.openImagesFolder()
    } catch (error) {
      console.error("Failed to open folder:", error)
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
          <div className="admin-card analytics-card">
            <h3>Daily Production Analytics (OK vs NG)</h3>
            <div className="chart-container">
              {loadingStats ? (
                <div className="loading-placeholder">Loading charts...</div>
              ) : (
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
              )}
            </div>
          </div>

          <div className="quick-actions-container">
            <button className="quick-action-btn-primary" onClick={handleOpenFolder}>
              <span className="icon">📁</span>
              Open Saved Images
            </button>
            <button className="quick-action-btn-secondary">
              <span className="icon">⚙️</span>
              Placeholder Action
            </button>
          </div>
        </div>

        {/* Right Section (30%) */}
        <div className="dashboard-right-panel">
          <div className="admin-card agent-sidebar">
            <h3>AI System Agent</h3>
            <div className="agent-display">
              <p className="agent-msg-sidebar">
                {isAsking ? "Processing request..." : (modelStatus?.message || "Ready for your command.")}
              </p>
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
