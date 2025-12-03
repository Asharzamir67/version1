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
    console.log(`CameraFeed ${cameraId}: stream received:`, stream ? 'YES' : 'NO', 'videoRef:', videoRef.current ? 'READY' : 'NULL')
    
    if (!stream) {
      console.log(`CameraFeed ${cameraId}: No stream yet, waiting...`)
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
      console.log(`CameraFeed ${cameraId}: Setting srcObject`)
      
      // Set the stream
      video.srcObject = stream
      
      // Ensure video plays
      const handleLoadedMetadata = () => {
        console.log(`CameraFeed ${cameraId}: Metadata loaded, attempting to play`)
        setLoading(false)
        setError(null)
        video.play().then(() => {
          console.log(`CameraFeed ${cameraId}: Video is playing successfully`)
        }).catch(err => {
          console.error(`CameraFeed ${cameraId}: Video play error:`, err)
          setError('Video playback error: ' + err.message)
          setLoading(false)
        })
      }
      
      const handlePlay = () => {
        console.log(`CameraFeed ${cameraId}: Video play event fired`)
      }
      
      const handlePlaying = () => {
        console.log(`CameraFeed ${cameraId}: Video is actually playing now`)
        setLoading(false)
        setError(null)
      }
      
      const handleError = (e) => {
        console.error(`CameraFeed ${cameraId}: Video error:`, e)
        setError('Video playback error')
        setLoading(false)
      }
      
      // Add event listeners
      video.addEventListener('loadedmetadata', handleLoadedMetadata)
      video.addEventListener('play', handlePlay)
      video.addEventListener('playing', handlePlaying)
      video.addEventListener('error', handleError)
      
      // Try to play immediately if metadata already loaded
      if (video.readyState >= 2) {
        console.log(`CameraFeed ${cameraId}: Video readyState is ${video.readyState}, playing immediately`)
        handleLoadedMetadata()
      } else {
        // Wait for metadata
        console.log(`CameraFeed ${cameraId}: Waiting for metadata, readyState: ${video.readyState}`)
      }
      
      // Store cleanup function
      cleanup = () => {
        video.removeEventListener('loadedmetadata', handleLoadedMetadata)
        video.removeEventListener('play', handlePlay)
        video.removeEventListener('playing', handlePlaying)
        video.removeEventListener('error', handleError)
      }
    }
    
    // Start setup
    setupVideo()
    
    // Return cleanup function
    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
      if (cleanup) {
        cleanup()
      }
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
    return status === 'good' ? 'Good' : 'NG'
  }

  return (
    <div className="camera-feed">
      <div className="camera-header">
        <h3>{name}</h3>
        <div className={`camera-status ${getStatusClass()}`}>
          {getStatusText()}
        </div>
      </div>
      
      <div className="camera-viewport">
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
    <div className="loading-spinner">Loading Camera Feed...</div>
  )}

  {error && (
    <div className="camera-placeholder">
      <div className="placeholder-content">
        <p>{error}</p>
        <small className="camera-id">ID: {cameraId}</small>
      </div>
    </div>
  )}
</div>

      </div>

      <div className="camera-footer">
        <div className={`status-indicator ${getStatusClass()}`}>
          <span className="status-dot"></span>
          <span className="status-label">{getStatusText()}</span>
        </div>
      </div>
    </div>
  )
})

export default CameraFeed

