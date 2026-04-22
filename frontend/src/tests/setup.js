import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Mock MediaStream
global.MediaStream = class {
  constructor() {}
  getTracks() {
    return [{ stop: vi.fn(), label: 'mock-track' }];
  }
}

// Mock localStorage
const localStorageMock = (() => {
  let store = {}
  return {
    getItem: vi.fn((key) => store[key] || null),
    setItem: vi.fn((key, value) => {
      store[key] = value.toString()
    }),
    removeItem: vi.fn((key) => {
      delete store[key]
    }),
    clear: vi.fn(() => {
      store = {}
    }),
  }
})()

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
})

// Mock navigator.mediaDevices
Object.defineProperty(navigator, 'mediaDevices', {
  value: {
    getUserMedia: vi.fn().mockResolvedValue(new MediaStream()),
    enumerateDevices: vi.fn().mockResolvedValue([
      { kind: 'videoinput', deviceId: 'cam1', label: 'Camera 1' },
      { kind: 'videoinput', deviceId: 'cam2', label: 'Camera 2' },
      { kind: 'videoinput', deviceId: 'cam3', label: 'Camera 3' },
      { kind: 'videoinput', deviceId: 'cam4', label: 'Camera 4' },
    ]),
  },
  configurable: true,
})

// Mock window.electronAPI
window.electronAPI = {
  getUserMedia: vi.fn().mockResolvedValue(new MediaStream()),
  enumerateDevices: vi.fn().mockResolvedValue([
    { kind: 'videoinput', deviceId: 'cam1', label: 'Camera 1' },
  ]),
}

// Mock HTMLCanvasElement
window.HTMLCanvasElement.prototype.toBlob = vi.fn().mockImplementation((callback) => {
  callback(new Blob([''], { type: 'image/jpeg' }))
})
window.HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue({
  fillRect: vi.fn(),
  fillText: vi.fn(),
  drawImage: vi.fn(),
  getImageData: vi.fn(),
  putImageData: vi.fn(),
  createImageData: vi.fn(),
  setTransform: vi.fn(),
  drawInlineVideo: vi.fn(),
})

// Mock ResizeObserver (needed for recharts/layout)
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock JSZip
vi.mock('jszip', () => {
  return {
    default: vi.fn().mockImplementation(() => ({
      loadAsync: vi.fn().mockResolvedValue({
        file: vi.fn().mockReturnValue({
          async: vi.fn().mockResolvedValue('{"summary": []}')
        })
      })
    }))
  }
})

// Mock scrollIntoView
window.HTMLElement.prototype.scrollIntoView = vi.fn()

// Mock Animation Frame APIs (needed for recharts and sync stability)
global.requestAnimationFrame = vi.fn((cb) => {
  cb()
  return 1
})
global.cancelAnimationFrame = vi.fn()
