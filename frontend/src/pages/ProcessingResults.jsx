import { useLocation, useNavigate } from 'react-router-dom';
import './ProcessingResults.css';

function ProcessingResults() {
  const location = useLocation();
  const navigate = useNavigate();
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
          <span style={{ color: '#cbd5e1', fontSize: '13px', marginRight: '8px' }}>
            Batch Status: <strong className={`summary-status ${overallStatusClass}`}>{overallStatusText}</strong>
          </span>
          <button className="back-button" onClick={() => navigate('/worker-dashboard')}>Process Next Batch</button>
        </div>
      </div>

      <div className="results-grid">
        {result.images && result.images.map((imageData, index) => {
          const predictions = typeof imageData.predictions === 'string'
            ? JSON.parse(imageData.predictions)
            : imageData.predictions;

          const hasDefects = imageData.defect === 'notgood'; // Simplified for display

          return (
            <div key={index} className="result-card">
              {/* Image */}
              <div className="result-image-container">
                {imageData.visualized ? (
                  <img
                    src={`data:image/png;base64,${imageData.visualized}`}
                    alt={`Result ${index + 1}`}
                    className="result-image"
                  />
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

              {/* Overlay Bottom: Detections (optional, keeping minimal) */}
              <div className="predictions-overlay">
                Detections: {predictions?.boxes?.length || 0}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default ProcessingResults;
