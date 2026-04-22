import React from 'react';
import './AIInsights.css';

const AIInsights = ({ observations }) => {
  if (!observations || observations.length === 0) {
    return (
      <div className="no-insights">
        <p>No system observations yet. The AI Supervisor is monitoring in the background.</p>
      </div>
    );
  }

  const getSeverityClass = (severity) => {
    switch (severity?.toUpperCase()) {
      case 'CRITICAL': return 'severity-critical';
      case 'WARNING': return 'severity-warning';
      default: return 'severity-info';
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  return (
    <div className="ai-insights-container">
      <h3>AI Autonomous Observations</h3>
      <div className="insights-list">
        {observations.map((obs) => (
          <div key={obs.id} className={`insight-card ${getSeverityClass(obs.severity)}`}>
            <div className="insight-header">
              <span className="insight-category">{obs.category}</span>
              <span className="insight-time">{formatDate(obs.created_at)}</span>
            </div>
            <p className="insight-text">{obs.observation}</p>
            <div className="insight-footer">
              <span className="severity-label">{obs.severity}</span>
              {obs.action_taken && (
                <span className="action-tag">Action: {obs.action_taken}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AIInsights;
