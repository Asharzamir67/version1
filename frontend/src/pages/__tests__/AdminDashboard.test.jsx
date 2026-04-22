import { vi, describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AdminDashboard from '../AdminDashboard'
import { authAPI } from '../../services/api'

// Mock Charts component
vi.mock('../../components/Charts', () => ({
  ResponsiveContainer: ({ children }) => <div>{children}</div>,
  BarChart: ({ children }) => <div>{children}</div>,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  Bar: () => null,
}))

// Mock authAPI
vi.mock('../../services/api', () => ({
  authAPI: {
    getModelStatus: vi.fn(),
    getDailyStats: vi.fn(),
    openImagesFolder: vi.fn(),
  },
}))

describe('Admin Dashboard AI Chat', () => {
  const mockUser = { username: 'admin', role: 'admin' }
  const mockOnLogout = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    authAPI.getDailyStats.mockResolvedValue({ data: [] })
    authAPI.getModelStatus.mockResolvedValue({ data: { message: 'System Ready' } })
  })

  it('should render AI System Agent panel', async () => {
    render(
      <MemoryRouter>
        <AdminDashboard user={mockUser} onLogout={mockOnLogout} />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('AI System Agent')).toBeInTheDocument()
      expect(screen.getByText('System Ready')).toBeInTheDocument()
    })
  })

  it('should handle AI agent interaction (Chat Maintenance)', async () => {
    // Initial mount call returns 'System Ready' (from beforeEach)
    
    render(
      <MemoryRouter>
        <AdminDashboard user={mockUser} onLogout={mockOnLogout} />
      </MemoryRouter>
    )

    // Wait for initial load to finish
    await waitFor(() => {
      expect(screen.getByText('System Ready')).toBeInTheDocument()
    })

    // Prepare next call
    authAPI.getModelStatus.mockResolvedValueOnce({ data: { message: 'Model is running well.' } })

    const textarea = screen.getByPlaceholderText('Ask agent...')
    const sendButton = screen.getByRole('button', { name: /Send/i })

    fireEvent.change(textarea, { target: { value: 'How is the model?' } })
    fireEvent.click(sendButton)

    // Use a longer timeout for the final response if needed
    await waitFor(() => {
      expect(authAPI.getModelStatus).toHaveBeenCalledWith('How is the model?')
      expect(screen.getByText('Model is running well.')).toBeInTheDocument()
    }, { timeout: 3000 })
  })
})
