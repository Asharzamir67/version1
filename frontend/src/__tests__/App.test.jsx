import { vi, describe, it, expect, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AppContent } from '../App'

// Mock components
vi.mock('../pages/Welcome', () => ({ default: () => <div data-testid="welcome-page">Welcome</div> }))
vi.mock('../pages/Login', () => ({ default: () => <div data-testid="login-page">Login</div> }))
vi.mock('../pages/WorkerDashboard', () => ({ 
  default: ({ onLogout }) => (
    <div data-testid="worker-dashboard">
      <h1>Worker Panel</h1>
      <button onClick={() => window.location.href = '#/processing-results'}>Capture</button>
      <button onClick={onLogout}>Logout</button>
    </div>
  ) 
}))
vi.mock('../pages/AdminDashboard', () => ({ default: () => <div data-testid="admin-dashboard">Admin Dashboard</div> }))
vi.mock('../pages/ProcessingResults', () => ({ default: () => <div data-testid="results-page">Processing Results</div> }))

// Exported auth utility for mocking
vi.mock('../utils/auth', () => ({
  isTokenExpired: vi.fn(() => false)
}))

import { isTokenExpired } from '../utils/auth'

describe('App Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('should render Welcome page by default at /', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <AppContent />
      </MemoryRouter>
    )
    expect(screen.getByTestId('welcome-page')).toBeInTheDocument()
  })

  it('should render dashboard if user is in localStorage and at /worker-dashboard', async () => {
    const mockUser = { username: 'worker1', role: 'worker', raw: { access_token: 'valid' } }
    localStorage.setItem('user', JSON.stringify(mockUser))

    render(
      <MemoryRouter initialEntries={['/worker-dashboard']}>
        <AppContent />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('worker-dashboard')).toBeInTheDocument()
      expect(screen.getByText(/Worker Panel/i)).toBeInTheDocument()
    })
  })

  it('should redirect back to welcome if unauthenticated tries to access dashboard', async () => {
    render(
      <MemoryRouter initialEntries={['/admin-dashboard']}>
        <AppContent />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('welcome-page')).toBeInTheDocument()
    })
  })

  it('should clear user and redirect if token is expired on mount', async () => {
    isTokenExpired.mockReturnValue(true)
    const mockUser = { username: 'worker1', role: 'worker', raw: { access_token: 'expired_token' } }
    localStorage.setItem('user', JSON.stringify(mockUser))

    render(
      <MemoryRouter initialEntries={['/worker-dashboard']}>
        <AppContent />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('welcome-page')).toBeInTheDocument()
      expect(localStorage.getItem('user')).toBeNull()
    })
  })
})
