import { useLocation, useNavigate } from 'react-router-dom';
import './ProcessingResults.css';

function ProcessingResults() {
  const location = useLocation();
  const navigate = useNavigate();
  const result = location.state?.result;

  if (!result) {
    return (
      <div className="results-container">
        <div className="results-card">
          <h2>No Results Found</h2>
          <p>Please process images first.</p>
          <button className="login-button" onClick={() => navigate('/worker-dashboard')}>
            Go to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="results-container">
      <div className="results-header">
        <h1>Processing Results</h1>
        <button className="back-button" onClick={() => navigate('/worker-dashboard')}>
          ← Back to Dashboard
        </button>
      </div>

      <div className="results-summary">
        <div className={`status-badge status-${result.status}`}>
          <span className="status-icon">
            {result.status === 'notgood' ? '❌' : '✅'}
          </span>
          <div>
            <h2>Overall Status: {result.status === 'notgood' ? 'NG (Not Good)' : 'OK (Good)'}</h2>
            <p>Model: {result.model}</p>
          </div>
        </div>
      </div>

      <div className="results-grid">
        {result.images && result.images.map((imageData, index) => {
          const predictions = typeof imageData.predictions === 'string'
            ? JSON.parse(imageData.predictions)
            : imageData.predictions;

          const hasDefects = imageData.defect === 'notgood' ||
            predictions?.boxes?.length > 0 ||
            (predictions?.masks && predictions.masks.length > 0);

          return (
            <div key={index} className="result-card">
              <div className="result-card-header">
                <h3>Image {index + 1}</h3>
                <div className={`result-status ${hasDefects ? 'status-ng' : 'status-good'}`}>
                  {hasDefects ? 'NG' : 'Good'}
                </div>
              </div>

              <div className="result-image-container">
                {imageData.visualized ? (
                  <img
                    src={`data:image/png;base64,${imageData.visualized}`}
                    alt={`Processed ${imageData.filename || `Image ${index + 1}`}`}
                    className="result-image"
                  />
                ) : (
                  <div className="no-image">No visualization available</div>
                )}
              </div>

              <div className="result-details">
                <p><strong>Filename:</strong> {imageData.filename || `Image ${index + 1}`}</p>
                {predictions && (
                  <div className="predictions-info">
                    <p><strong>Detections:</strong> {predictions.boxes?.length || 0}</p>
                    {predictions.boxes && predictions.boxes.length > 0 && (
                      <div className="detections-list">
                        {predictions.boxes.map((box, boxIdx) => (
                          <div key={boxIdx} className="detection-item">
                            <span>Box {boxIdx + 1}</span>
                            {box.conf && <span>Confidence: {(box.conf * 100).toFixed(1)}%</span>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="results-actions">
        <button className="login-button" onClick={() => navigate('/worker-dashboard')}>
          Process More Images
        </button>
      </div>
    </div>
  );
}

export default ProcessingResults;

