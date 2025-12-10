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

  // Full Screen on Mount
  useEffect(() => {
    const enterFullScreen = async () => {
      try {
        if (document.documentElement.requestFullscreen) {
          await document.documentElement.requestFullscreen()
        }
      } catch (e) {
        console.log("Full screen denied", e)
      }
    }
    enterFullScreen()
  }, [])

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
  const [metadataText, setMetadataText] = useState('default')
  const [processing, setProcessing] = useState(false)
  const [processResult, setProcessResult] = useState(null)
  const [capturedImages, setCapturedImages] = useState([])
  const [captureModalOpen, setCaptureModalOpen] = useState(false)

  // Refs for camera video elements
  const frontend1Ref = useRef(null)
  const frontend2Ref = useRef(null)
  const backend1Ref = useRef(null)
  const backend2Ref = useRef(null)
  const metadataInputRef = useRef(null)

  // Helper functions for Electron / Web compatibility
  const getMedia = async (constraints) => {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      return await navigator.mediaDevices.getUserMedia(constraints)
    }
    if (window.electronAPI?.getUserMedia) {
      return await window.electronAPI.getUserMedia(constraints)
    }
    throw new Error('getUserMedia not available')
  }

  const enumerateDevices = async () => {
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

  // Auto-focus the text input on mount
  useEffect(() => {
    if (metadataInputRef.current) {
      metadataInputRef.current.focus()
    }
  }, [])

  const handleLogout = () => setShowLogoutConfirm(true)
  const confirmLogout = () => {
    if (document.exitFullscreen) {
      document.exitFullscreen().catch(err => console.log(err));
    }
    setShowLogoutConfirm(false);
    onLogout()
  }
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
      if (!videoElement ||
        !videoElement.videoWidth ||
        !videoElement.videoHeight ||
        videoElement.videoWidth === 0 ||
        videoElement.videoHeight === 0 ||
        videoElement.readyState < 2) {
        console.log(`Camera ${cameraId}: No video available, creating empty image`)
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
            createEmptyImage().then(resolve)
            return
          }
          const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
          const filename = `${cameraId}_${timestamp}.jpg`
          const file = new File([blob], filename, { type: 'image/jpeg' })
          resolve(file)
        }, 'image/jpeg', 0.9)
      } catch (err) {
        createEmptyImage().then(resolve)
      }
    })
  }

  // Capture all camera feeds
  const handleCaptureFeeds = async () => {
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
    setMetadataText('default')
  }

  if (!user || user.role !== 'worker') return null

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-left">
          <img src={logo} alt="Logo" className="dashboard-logo" />
          <div className="header-content">
            <h1>Worker Panel</h1>
          </div>
        </div>
        <button className="logout-button" onClick={handleLogout} title="Exit Fullscreen & Logout">✕</button>
      </header>

      <main className="dashboard-content">
        <div className="input-section">
          {/* Horizontal Layout: Input | Process | Capture | Status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontWeight: 'bold', fontSize: '14px', whiteSpace: 'nowrap' }}>Batch:</span>
            <input
              ref={metadataInputRef}
              type="text"
              value={metadataText}
              onChange={(e) => setMetadataText(e.target.value)}
              placeholder="Scan barcode..."
              style={{
                width: '180px', /* Reduced width */
                padding: '6px 12px',
                fontSize: '16px',
                borderRadius: '4px',
                border: '1px solid #2196F3',
                textAlign: 'center'
              }}
            />
          </div>

          <button className="login-button" style={{ padding: '6px 16px', fontSize: '14px', whiteSpace: 'nowrap' }} onClick={() => setProcessingModalOpen(true)}>Process</button>
          <button className="login-button" style={{ padding: '6px 16px', fontSize: '14px', backgroundColor: '#4CAF50', whiteSpace: 'nowrap' }} onClick={handleCaptureFeeds}>Capture</button>

          {processResult && (
            <div style={{ padding: '4px 8px', fontSize: '12px', borderRadius: '4px', backgroundColor: processResult.status === 'notgood' ? '#ffebee' : '#e8f5e9', border: `1px solid ${processResult.status === 'notgood' ? '#ef5350' : '#66bb6a'}`, whiteSpace: 'nowrap' }}>
              <strong>Last:</strong> {processResult.status}
            </div>
          )}
        </div>

        {/* Unified 2x2 Grid */}
        <div className="camera-grid">
          <div className="camera-cell">
            <CameraFeed
              ref={frontend1Ref}
              name="Frontend 1"
              cameraId="frontend1"
              status={cameraStatuses.frontend1}
              stream={cameraStreams.frontend1}
            />
          </div>
          <div className="camera-cell">
            <CameraFeed
              ref={frontend2Ref}
              name="Frontend 2"
              cameraId="frontend2"
              status={cameraStatuses.frontend2}
              stream={cameraStreams.frontend2}
            />
          </div>
          <div className="camera-cell">
            <CameraFeed
              ref={backend1Ref}
              name="Backend 1"
              cameraId="backend1"
              status={cameraStatuses.backend1}
              stream={cameraStreams.backend1}
            />
          </div>
          <div className="camera-cell">
            <CameraFeed
              ref={backend2Ref}
              name="Backend 2"
              cameraId="backend2"
              status={cameraStatuses.backend2}
              stream={cameraStreams.backend2}
            />
          </div>
        </div>

        <div className="summary-section">
          <div style={{ fontSize: '10px', color: '#666' }}>Logged in as {user.username}</div>
          <div className="summary-grid">
            <div className="summary-item">
              <span>Good:</span>
              <span className="summary-value good">
                {Object.values(cameraStatuses).filter(s => s === 'good').length}
              </span>
            </div>
            <div className="summary-item">
              <span>NG:</span>
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
            <h3>Exit Dashboard?</h3>
            <p>This will log you out.</p>
            <div className="modal-actions">
              <button className="button-secondary" onClick={cancelLogout}>Cancel</button>
              <button className="button-danger" onClick={confirmLogout}>Exit</button>
            </div>
          </div>
        </div>
      )}
      {/* ... keeping processing modal mostly same, just ensuring variables are correct ... */}
      {processingModalOpen && (
        <div className="modal-overlay" role="dialog" aria-modal="true">
          <div className="modal-card">
            <h3>Process Images</h3>
            <form onSubmit={async (e) => {
              e.preventDefault()
              if (selectedFiles.length !== 4) {
                alert('Please select exactly 4 images')
                return
              }

              setProcessing(true)
              setProcessResult(null)

              try {
                const response = await imageAPI.processImages(selectedFiles, selectedModel, metadataText)

                const zip = new JSZip();
                const unzipped = await zip.loadAsync(response.data);
                const resultsJson = await unzipped.file("results.json").async("string");
                const results = JSON.parse(resultsJson);

                const processedImages = [];
                for (const item of results.summary) {
                  const filename = item.filename;
                  const imgFile = unzipped.file(`processed/${filename}`);
                  if (imgFile) {
                    const imgBlob = await imgFile.async("blob");
                    const base64 = await new Promise((resolve) => {
                      const reader = new FileReader();
                      reader.onloadend = () => resolve(reader.result.split(',')[1]);
                      reader.readAsDataURL(imgBlob);
                    });

                    processedImages.push({
                      filename: filename,
                      visualized: base64,
                      predictions: {},
                      defect: item.defect
                    });
                  }
                }

                const overallStatus = processedImages.some(img => img.defect === 'notgood') ? 'notgood' : 'good';

                const finalResult = {
                  status: overallStatus,
                  model: results.model,
                  images: processedImages
                };

                setProcessResult(finalResult)

                if (finalResult.status === 'notgood') {
                  setCameraStatuses(prev => ({ ...prev, frontend1: 'ng', frontend2: 'ng', backend1: 'ng', backend2: 'ng' }))
                } else {
                  setCameraStatuses(prev => ({ ...prev, frontend1: 'good', frontend2: 'good', backend1: 'good', backend2: 'good' }))
                }

                setProcessingModalOpen(false);
                setTimeout(() => {
                  navigate('/processing-results', {
                    state: { result: finalResult }
                  });
                }, 100);
              } catch (err) {
                const errorMessage = err.response?.data?.detail || err.message || 'Processing failed'
                alert('Processing error: ' + errorMessage)
              } finally {
                setProcessing(false)
                setProcessingModalOpen(false)
              }
            }}>
              <div style={{ marginBottom: 8 }}>
                <label>Model</label>
                <input value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)} style={{ marginLeft: 8 }} />
              </div>
              <div style={{ marginBottom: 8 }}>
                <input type="file" accept="image/*" multiple onChange={(e) => setSelectedFiles(Array.from(e.target.files))} />
              </div>
              <div className="modal-actions">
                <button type="button" className="button-secondary" onClick={() => setProcessingModalOpen(false)}>Cancel</button>
                <button type="submit" className="login-button" disabled={processing}>{processing ? '...' : 'Submit'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
      {captureModalOpen && (
        <div className="modal-overlay" role="dialog" aria-modal="true">
          <div className="modal-card">
            <h3>Captured</h3>
            <p>{capturedImages.length} images.</p>
            <div className="modal-actions">
              <button type="button" className="button-secondary" onClick={() => { setCaptureModalOpen(false); setCapturedImages([]) }}>Cancel</button>
              <button type="button" className="login-button" onClick={handleProcessCaptured}>Process</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default WorkerDashboard
