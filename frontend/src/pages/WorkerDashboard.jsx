import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import JSZip from 'jszip'
import CameraFeed from '../components/CameraFeed'
import logo from '../components/logo.png'
import './WorkerDashboard.css'
import { imageAPI } from '../services/api'

function WorkerDashboard({ user, onLogout }) {
  const navigate = useNavigate()

  useEffect(() => {
    if (!user || user.role !== 'worker') {
      navigate('/', { replace: true })
    }
  }, [user, navigate])

  const [cameraStatuses, setCameraStatuses] = useState({
    frontend1: 'good',
    frontend2: 'good',
    backend1: 'ng',
    backend2: 'good'
  })

  const [cameraStreams, setCameraStreams] = useState({
    frontend1: null,
    frontend2: null,
    backend1: null,
    backend2: null
  })

  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false)
  const [processingModalOpen, setProcessingModalOpen] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState([])
  const [selectedModel, setSelectedModel] = useState('default')
  const [processing, setProcessing] = useState(false)
  const [processResult, setProcessResult] = useState(null)
  const [capturedImages, setCapturedImages] = useState([])
  const [captureModalOpen, setCaptureModalOpen] = useState(false)

  // Refs for camera video elements
  const frontend1Ref = useRef(null)
  const frontend2Ref = useRef(null)
  const backend1Ref = useRef(null)
  const backend2Ref = useRef(null)

  // Helper functions for Electron / Web compatibility
  const getMedia = async (constraints) => {
    // Prefer the renderer's native API when available —
    // MediaStream objects cannot be serialized across the contextBridge,
    // so calling `electronAPI.getUserMedia` from preload can fail.
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      return await navigator.mediaDevices.getUserMedia(constraints)
    }
    if (window.electronAPI?.getUserMedia) {
      return await window.electronAPI.getUserMedia(constraints)
    }
    throw new Error('getUserMedia not available')
  }

  const enumerateDevices = async () => {
    // Prefer renderer API; fallback to preload if needed
    if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
      return await navigator.mediaDevices.enumerateDevices()
    }
    if (window.electronAPI?.enumerateDevices) {
      return await window.electronAPI.enumerateDevices()
    }
    return []
  }

  useEffect(() => {
    const initCameras = async () => {
      if (!navigator.mediaDevices && !window.electronAPI?.getUserMedia) {
        console.error('Camera API not supported')
        return
      }

      try {
        await getMedia({ video: true }) // permission check
      } catch (err) {
        alert('Camera permission is required.')
        return
      }

      const devices = await enumerateDevices()
      const videoInputs = devices.filter(d => d.kind === 'videoinput')

      const cameraIds = ['frontend1', 'frontend2', 'backend1', 'backend2']
      const streams = {}

      for (let i = 0; i < cameraIds.length; i++) {
        const camId = cameraIds[i]
        if (i < videoInputs.length) {
          try {
            const stream = await getMedia({
              video: { deviceId: { exact: videoInputs[i].deviceId }, width: 1280, height: 720 }
            })
            streams[camId] = stream
          } catch (err) {
            console.error(`Camera ${camId} failed:`, err)
            streams[camId] = null
          }
        } else streams[camId] = null
      }

      setCameraStreams(streams)
    }

    initCameras()

    return () => {
      Object.values(cameraStreams).forEach(stream => {
        if (stream) stream.getTracks().forEach(track => track.stop())
      })
    }
  }, [])

  // Simulate camera status changes (demo)
  useEffect(() => {
    const interval = setInterval(() => {
      setCameraStatuses(prev => {
        const newStatus = { ...prev }
        const cams = ['frontend1', 'frontend2', 'backend1', 'backend2']
        const randomCam = cams[Math.floor(Math.random() * cams.length)]
        newStatus[randomCam] = Math.random() > 0.5 ? 'good' : 'ng'
        return newStatus
      })
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  const handleLogout = () => setShowLogoutConfirm(true)
  const confirmLogout = () => { setShowLogoutConfirm(false); onLogout() }
  const cancelLogout = () => setShowLogoutConfirm(false)

  // Create an empty image (1x1 transparent PNG as base64)
  const createEmptyImage = () => {
    const canvas = document.createElement('canvas')
    canvas.width = 1280
    canvas.height = 720
    const ctx = canvas.getContext('2d')
    ctx.fillStyle = '#000000'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.fillStyle = '#ffffff'
    ctx.font = '48px Arial'
    ctx.textAlign = 'center'
    ctx.fillText('No Camera', canvas.width / 2, canvas.height / 2)
    return new Promise((resolve) => {
      canvas.toBlob((blob) => {
        const file = new File([blob], 'empty.jpg', { type: 'image/jpeg' })
        resolve(file)
      }, 'image/jpeg', 0.8)
    })
  }

  // Capture frame from video element
  const captureVideoFrame = (videoElement, cameraId) => {
    return new Promise((resolve) => {
      // Check if video element exists and has valid dimensions
      if (!videoElement ||
        !videoElement.videoWidth ||
        !videoElement.videoHeight ||
        videoElement.videoWidth === 0 ||
        videoElement.videoHeight === 0 ||
        videoElement.readyState < 2) {
        console.log(`Camera ${cameraId}: No video available (readyState: ${videoElement?.readyState || 'N/A'}), creating empty image`)
        createEmptyImage().then(resolve)
        return
      }

      try {
        const canvas = document.createElement('canvas')
        canvas.width = videoElement.videoWidth
        canvas.height = videoElement.videoHeight
        const ctx = canvas.getContext('2d')
        ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height)

        canvas.toBlob((blob) => {
          if (!blob) {
            console.error(`Camera ${cameraId}: Failed to create blob, using empty image`)
            createEmptyImage().then(resolve)
            return
          }
          const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
          const filename = `${cameraId}_${timestamp}.jpg`
          const file = new File([blob], filename, { type: 'image/jpeg' })
          console.log(`Camera ${cameraId}: Captured image ${filename} (${(blob.size / 1024).toFixed(2)} KB)`)
          resolve(file)
        }, 'image/jpeg', 0.9)
      } catch (err) {
        console.error(`Camera ${cameraId}: Error capturing frame:`, err)
        createEmptyImage().then(resolve)
      }
    })
  }

  // Capture all camera feeds
  const handleCaptureFeeds = async () => {
    const timestamp = new Date().toLocaleString()
    console.log(`\n[${timestamp}] 📸 FRONTEND: Capturing all camera feeds`)

    const cameraRefs = {
      frontend1: frontend1Ref,
      frontend2: frontend2Ref,
      backend1: backend1Ref,
      backend2: backend2Ref
    }

    const captured = []
    for (const [cameraId, ref] of Object.entries(cameraRefs)) {
      const videoElement = ref.current
      const image = await captureVideoFrame(videoElement, cameraId)
      captured.push(image)
    }

    setCapturedImages(captured)
    setCaptureModalOpen(true)

    console.log(`  ✅ Captured ${captured.length} images`)
    captured.forEach((img, idx) => {
      console.log(`    ${idx + 1}. ${img.name} (${(img.size / 1024).toFixed(2)} KB)`)
    })
  }

  // Process captured images
  const handleProcessCaptured = async () => {
    if (capturedImages.length !== 4) {
      alert('Expected 4 captured images')
      return
    }

    setCaptureModalOpen(false)
    setProcessingModalOpen(true)
    setSelectedFiles(capturedImages)
    setSelectedModel('default')
  }

  if (!user || user.role !== 'worker') return null

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-left">
          <img src={logo} alt="Logo" className="dashboard-logo" />
          <div className="header-content">
            <h1>Team Member Dashboard</h1>
            <p className="user-info">Welcome, {user.username}</p>
          </div>
        </div>
        <button className="logout-button" onClick={handleLogout}>Logout</button>
      </header>

      <main className="dashboard-content">
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <button className="login-button" onClick={() => setProcessingModalOpen(true)}>Process Images</button>
            {processResult && (
              <div style={{ marginTop: 0 }}>
                <strong>Status:</strong> {processResult.status}
              </div>
            )}
          </div>
          <button className="login-button" onClick={handleCaptureFeeds}>Capture Feed</button>
        </div>
        <div className="camera-grid">
          <div className="camera-section">
            <h2 className="section-title">Frontend Cameras</h2>
            <div className="camera-group">
              <CameraFeed
                ref={frontend1Ref}
                name="Frontend Camera 1"
                cameraId="frontend1"
                status={cameraStatuses.frontend1}
                stream={cameraStreams.frontend1}
              />
              <CameraFeed
                ref={frontend2Ref}
                name="Frontend Camera 2"
                cameraId="frontend2"
                status={cameraStatuses.frontend2}
                stream={cameraStreams.frontend2}
              />
            </div>
          </div>

          <div className="camera-section">
            <h2 className="section-title">Backend Cameras</h2>
            <div className="camera-group">
              <CameraFeed
                ref={backend1Ref}
                name="Backend Camera 1"
                cameraId="backend1"
                status={cameraStatuses.backend1}
                stream={cameraStreams.backend1}
              />
              <CameraFeed
                ref={backend2Ref}
                name="Backend Camera 2"
                cameraId="backend2"
                status={cameraStatuses.backend2}
                stream={cameraStreams.backend2}
              />
            </div>
          </div>
        </div>

        <div className="summary-section">
          <h3>System Summary</h3>
          <div className="summary-grid">
            <div className="summary-item">
              <span className="summary-label">Good Cases:</span>
              <span className="summary-value good">
                {Object.values(cameraStatuses).filter(s => s === 'good').length}
              </span>
            </div>
            <div className="summary-item">
              <span className="summary-label">NG Cases:</span>
              <span className="summary-value ng">
                {Object.values(cameraStatuses).filter(s => s === 'ng').length}
              </span>
            </div>
          </div>
        </div>
      </main>

      {showLogoutConfirm && (
        <div className="modal-overlay" role="dialog" aria-modal="true">
          <div className="modal-card">
            <h3>Confirm Logout</h3>
            <p>Are you sure you want to end this session?</p>
            <div className="modal-actions">
              <button className="button-secondary" onClick={cancelLogout}>Cancel</button>
              <button className="button-danger" onClick={confirmLogout}>Logout</button>
            </div>
          </div>
        </div>
      )}
      {processingModalOpen && (
        <div className="modal-overlay" role="dialog" aria-modal="true">
          <div className="modal-card">
            <h3>Process Images (exactly 4)</h3>
            <form onSubmit={async (e) => {
              e.preventDefault()
              if (selectedFiles.length !== 4) {
                alert('Please select exactly 4 images')
                return
              }

              setProcessing(true)
              setProcessResult(null)

              try {
                const timestamp = new Date().toLocaleString();
                console.log(`\n[${timestamp}] 🖼️  FRONTEND: Image processing request`);
                console.log(`  Model: ${selectedModel}`);
                console.log(`  Images: ${selectedFiles.length} files`);
                selectedFiles.forEach((file, idx) => {
                  console.log(`    ${idx + 1}. ${file.name} (${(file.size / 1024).toFixed(2)} KB)`);
                });

                const response = await imageAPI.processImages(selectedFiles, selectedModel, 'default')

                // Handle ZIP response
                const zip = new JSZip();
                const unzipped = await zip.loadAsync(response.data);

                // Read results.json
                const resultsJson = await unzipped.file("results.json").async("string");
                const results = JSON.parse(resultsJson);

                // Process images
                const processedImages = [];
                for (const item of results.summary) {
                  const filename = item.filename;
                  const imgFile = unzipped.file(`processed/${filename}`);
                  if (imgFile) {
                    const imgBlob = await imgFile.async("blob");
                    // Convert to base64 for compatibility with existing UI
                    const base64 = await new Promise((resolve) => {
                      const reader = new FileReader();
                      reader.onloadend = () => resolve(reader.result.split(',')[1]);
                      reader.readAsDataURL(imgBlob);
                    });

                    processedImages.push({
                      filename: filename,
                      visualized: base64,
                      predictions: {}, // No longer returned in summary
                      defect: item.defect // 'ok' or 'notgood'
                    });
                  }
                }

                // Determine overall status
                const overallStatus = processedImages.some(img => img.defect === 'notgood') ? 'notgood' : 'good';

                const finalResult = {
                  status: overallStatus,
                  model: results.model,
                  images: processedImages
                };

                setProcessResult(finalResult)

                console.log(`  ✅ Processing successful`);
                console.log(`  Status: ${finalResult.status}`);
                console.log(`  Results: ${finalResult.images?.length || 0} images processed`);

                // Update camera statuses based on result
                if (finalResult.status === 'notgood') {
                  console.log(`  ⚠️  Defects detected - Setting all cameras to NG`);
                  setCameraStatuses(prev => ({
                    ...prev,
                    frontend1: 'ng',
                    frontend2: 'ng',
                    backend1: 'ng',
                    backend2: 'ng'
                  }))
                } else {
                  console.log(`  ✅ No defects - Setting all cameras to Good`);
                  setCameraStatuses(prev => ({
                    ...prev,
                    frontend1: 'good',
                    frontend2: 'good',
                    backend1: 'good',
                    backend2: 'good'
                  }))
                }

                // Close modal first
                setProcessingModalOpen(false);

                // Navigate to results page with the result data
                setTimeout(() => {
                  navigate('/processing-results', {
                    state: { result: finalResult }
                  });
                }, 100);
              } catch (err) {
                const timestamp = new Date().toLocaleString();
                console.error(`\n[${timestamp}] ❌ FRONTEND: Image processing failed`);
                console.error(`  Error: ${err.message}`);
                console.error(`  Response:`, err.response?.data);
                const errorMessage = err.response?.data?.detail || err.message || 'Processing failed'
                alert('Processing error: ' + errorMessage)
              } finally {
                setProcessing(false)
                setProcessingModalOpen(false)
              }
            }}>
              <div style={{ marginBottom: 8 }}>
                <label>Model name</label>
                <input value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)} />
              </div>
              <div style={{ marginBottom: 8 }}>
                <input type="file" accept="image/*" multiple onChange={(e) => setSelectedFiles(Array.from(e.target.files))} />
                <div style={{ fontSize: 12, marginTop: 6 }}>{selectedFiles.length} files selected</div>
              </div>
              <div className="modal-actions">
                <button type="button" className="button-secondary" onClick={() => setProcessingModalOpen(false)}>Cancel</button>
                <button type="submit" className="login-button" disabled={processing}>{processing ? 'Processing…' : 'Submit'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
      {captureModalOpen && (
        <div className="modal-overlay" role="dialog" aria-modal="true">
          <div className="modal-card">
            <h3>Captured Images</h3>
            <p>Successfully captured {capturedImages.length} images from camera feeds.</p>
            <div style={{ marginBottom: 16, fontSize: 14, color: 'var(--text-secondary)' }}>
              {capturedImages.map((img, idx) => (
                <div key={idx} style={{ marginBottom: 4 }}>
                  {idx + 1}. {img.name} ({(img.size / 1024).toFixed(2)} KB)
                </div>
              ))}
            </div>
            <p style={{ marginBottom: 16 }}>Would you like to process these captured images?</p>
            <div className="modal-actions">
              <button
                type="button"
                className="button-secondary"
                onClick={() => {
                  setCaptureModalOpen(false)
                  setCapturedImages([])
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                className="login-button"
                onClick={handleProcessCaptured}
              >
                Process Images
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default WorkerDashboard
