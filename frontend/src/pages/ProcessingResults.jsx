import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import CanvasOverlay from '../components/CanvasOverlay';
import './ProcessingResults.css';

function ProcessingResults() {
  const location = useLocation();
  const navigate = useNavigate();
  const [showOverlays, setShowOverlays] = useState(true);
  const result = location.state?.result;

  if (!result) {
    return (
      <div className="results-container">
        <div className="results-header">
          <h1>No Results</h1>
          <button className="back-button" onClick={() => navigate('/worker-dashboard')}>Back</button>
        </div>
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>
          No data available.
        </div>
      </div>
    );
  }

  const overallStatusText = result.status === 'notgood' ? 'NG' : 'OK';
  const overallStatusClass = result.status === 'notgood' ? 'st-ng' : 'st-ok';

  return (
    <div className="results-container">
      <div className="results-header">
        <h1>Processing Results</h1>
        <div className="results-actions-header">
          <label className="toggle-container" style={{ display: 'flex', alignItems: 'center', marginRight: '16px', color: '#94a3b8', fontSize: '13px', cursor: 'pointer' }}>
             <input 
               type="checkbox" 
               checked={showOverlays} 
               onChange={() => setShowOverlays(!showOverlays)}
               style={{ marginRight: '6px' }}
             />
             Show AI Overlays
          </label>
          <span style={{ color: '#cbd5e1', fontSize: '13px', marginRight: '8px' }}>
            Batch Status: <strong className={`summary-status ${overallStatusClass}`}>{overallStatusText}</strong>
          </span>
          <button className="back-button" onClick={() => navigate('/worker-dashboard')}>Process Next Batch</button>
        </div>
      </div>

      <div className="results-grid">
        {result.images && result.images.map((imageData, index) => {
          const predictions = imageData.predictions;
          const hasDefects = imageData.defect === 'notgood';
          const overlayColor = hasDefects ? '#F44336' : '#4CAF50';

          return (
            <div key={index} className="result-card">
              {/* Image & Canvas Overlays */}
              <div className="result-image-container" style={{ position: 'relative' }}>
                {imageData.visualized ? (
                  <>
                    <img
                      src={`data:image/png;base64,${imageData.visualized}`}
                      alt={`Result ${index + 1}`}
                      className="result-image"
                      id={`img-result-${index}`}
                    />
                    {showOverlays && (
                      <CanvasOverlay 
                        predictions={predictions} 
                        color={overlayColor}
                      />
                    )}
                  </>
                ) : (
                  <div className="no-image">No Image</div>
                )}
              </div>

              {/* Overlay Top: Filename & Status */}
              <div className="result-overlay">
                <div className="result-filename">{imageData.filename || `Image ${index + 1}`}</div>
                <div className={`result-badge ${hasDefects ? 'st-ng' : 'st-good'}`}>
                  {hasDefects ? 'NG' : 'GOOD'}
                </div>
              </div>

              {/* Overlay Bottom: Detections */}
              <div className="predictions-overlay">
                Detections: {predictions?.length || 0}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default ProcessingResults;
