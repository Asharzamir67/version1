import { useState, useEffect, useRef, forwardRef } from 'react'
import './CameraFeed.css'

const CameraFeed = forwardRef(function CameraFeed({ name, cameraId, status, stream }, ref) {
  const videoRef = useRef(null)

  // Expose video element via ref
  useEffect(() => {
    if (ref) {
      if (typeof ref === 'function') {
        ref(videoRef.current)
      } else {
        ref.current = videoRef.current
      }
    }
  }, [ref, stream])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!stream) {
      setLoading(true)
      setError(null)
      return
    }

    // Wait for video element to be ready
    let cleanup = null
    let timeoutId = null

    const setupVideo = () => {
      if (!videoRef.current) {
        setTimeout(setupVideo, 100)
        return
      }

      const video = videoRef.current
      video.srcObject = stream

      const handleLoadedMetadata = () => {
        setLoading(false)
        setError(null)
        video.play().catch(err => {
          console.error(`CameraFeed ${cameraId}: Video play error:`, err)
          setError('Playback error')
          setLoading(false)
        })
      }

      const handlePlaying = () => {
        setLoading(false)
        setError(null)
      }

      const handleError = (e) => {
        console.error(`CameraFeed ${cameraId}: Video error:`, e)
        setError('Video error')
        setLoading(false)
      }

      // Add event listeners
      video.addEventListener('loadedmetadata', handleLoadedMetadata)
      video.addEventListener('playing', handlePlaying)
      video.addEventListener('error', handleError)

      // Try to play immediately if metadata already loaded
      if (video.readyState >= 2) {
        handleLoadedMetadata()
      }

      // Store cleanup function
      cleanup = () => {
        video.removeEventListener('loadedmetadata', handleLoadedMetadata)
        video.removeEventListener('playing', handlePlaying)
        video.removeEventListener('error', handleError)
      }
    }

    setupVideo()

    return () => {
      if (timeoutId) clearTimeout(timeoutId)
      if (cleanup) cleanup()
    }
  }, [stream, cameraId])

  // Cleanup stream when component unmounts
  useEffect(() => {
    return () => {
      if (videoRef.current && videoRef.current.srcObject) {
        const tracks = videoRef.current.srcObject.getTracks()
        tracks.forEach(track => track.stop())
      }
    }
  }, [])

  const getStatusClass = () => {
    return status === 'good' ? 'status-good' : 'status-ng'
  }

  const getStatusText = () => {
    return status === 'good' ? 'GOOD' : 'NG'
  }

  return (
    <div className="camera-feed">
      {/* Overlay Info */}
      <div className="camera-overlay">
        <div className="camera-name">{name}</div>
        <div className={`camera-status-badge ${getStatusClass()}`}>
          {getStatusText()}
        </div>
      </div>

      <div className="camera-viewport">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="camera-video"
          style={{ display: error ? 'none' : 'block' }}
        />

        {loading && !error && (
          <div className="loading-spinner">Loading...</div>
        )}

        {error && (
          <div className="camera-placeholder">
            <div className="placeholder-content">
              <p>{error}</p>
              <small className="camera-id">{cameraId}</small>
            </div>
          </div>
        )}
      </div>
    </div>
  )
})

export default CameraFeed
