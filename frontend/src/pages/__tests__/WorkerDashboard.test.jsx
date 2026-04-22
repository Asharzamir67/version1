import { vi, describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { HashRouter } from 'react-router-dom'
import WorkerDashboard from '../WorkerDashboard'
import { imageAPI } from '../../services/api'

// Mock components
vi.mock('../../components/CameraFeed', () => ({
  default: ({ name, status, ref }) => (
    <div data-testid={`camera-${name}`}>
      {name} {status}
    </div>
  ),
}))

// Mock imageAPI
vi.mock('../../services/api', () => ({
  imageAPI: {
    processImages: vi.fn(),
  },
}))

describe('Worker Dashboard Workflow', () => {
  const mockUser = { username: 'worker', role: 'worker' }
  const mockOnLogout = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock navigator.mediaDevices.getUserMedia
    vi.stubGlobal('navigator', {
      mediaDevices: {
        getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop: vi.fn() }] }),
        enumerateDevices: vi.fn().mockResolvedValue([
          { kind: 'videoinput', deviceId: 'dev1' },
          { kind: 'videoinput', deviceId: 'dev2' },
          { kind: 'videoinput', deviceId: 'dev3' },
          { kind: 'videoinput', deviceId: 'dev4' },
        ]),
      }
    })
  })

  it('should render 4 camera feeds with names', async () => {
    render(
      <HashRouter>
        <WorkerDashboard user={mockUser} onLogout={mockOnLogout} />
      </HashRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('camera-Frontend 1')).toBeInTheDocument()
      expect(screen.getByTestId('camera-Frontend 2')).toBeInTheDocument()
      expect(screen.getByTestId('camera-Backend 1')).toBeInTheDocument()
      expect(screen.getByTestId('camera-Backend 2')).toBeInTheDocument()
    })
  })

  it('should handle barcode/batch metadata input (Statefulness)', () => {
    render(
      <HashRouter>
        <WorkerDashboard user={mockUser} onLogout={mockOnLogout} />
      </HashRouter>
    )

    const input = screen.getByPlaceholderText('Scan barcode...')
    fireEvent.change(input, { target: { value: 'BATCH123' } })
    expect(input.value).toBe('BATCH123')
  })

  it('should handle camera capture and opening processing modal', async () => {
    // Capture button
    render(
      <HashRouter>
        <WorkerDashboard user={mockUser} onLogout={mockOnLogout} />
      </HashRouter>
    )

    const captureBtn = screen.getByRole('button', { name: /Capture/i })
    fireEvent.click(captureBtn)

    await waitFor(() => {
      expect(screen.getByText('Captured')).toBeInTheDocument()
      expect(screen.getByText('4 images.')).toBeInTheDocument()
    })

    const processBtn = screen.getAllByRole('button', { name: /Process/i })[0]
    fireEvent.click(processBtn)

    await waitFor(() => {
      expect(screen.getByText('Process Images')).toBeInTheDocument()
    })
  })
})
