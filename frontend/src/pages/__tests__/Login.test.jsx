import { vi, describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import Login from '../Login'
import { authAPI } from '../../services/api'

// Mock useNavigate
const mockedUsedNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockedUsedNavigate,
  }
})

// Mock authAPI
vi.mock('../../services/api', () => ({
  authAPI: {
    login: vi.fn(),
    adminLogin: vi.fn()
  },
  default: {
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() }
    }
  }
}))

describe('Login Page', () => {
  const mockOnLogin = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('should render login form with correct placeholders', () => {
    render(
      <MemoryRouter>
        <Login onLogin={mockOnLogin} />
      </MemoryRouter>
    )
    expect(screen.getByPlaceholderText('Enter your username')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Enter your password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Login/i })).toBeInTheDocument()
  })

  it('should call authAPI.login on form submission as user', async () => {
    authAPI.login.mockResolvedValueOnce({
      data: {
        access_token: 'valid_token'
      }
    })

    render(
      <MemoryRouter>
        <Login onLogin={mockOnLogin} />
      </MemoryRouter>
    )

    fireEvent.change(screen.getByPlaceholderText('Enter your username'), { target: { value: 'testuser' } })
    fireEvent.change(screen.getByPlaceholderText('Enter your password'), { target: { value: 'password123' } })
    fireEvent.click(screen.getByRole('button', { name: /Login/i }))

    await waitFor(() => {
      expect(authAPI.login).toHaveBeenCalledWith({ username: 'testuser', password: 'password123' })
    })

    expect(mockOnLogin).toHaveBeenCalledWith(expect.objectContaining({
      username: 'testuser',
      role: 'worker'
    }))
  })

  it('should call authAPI.adminLogin when role=admin search param is present', async () => {
    authAPI.adminLogin.mockResolvedValueOnce({
      data: {
        access_token: 'admin_token'
      }
    })

    render(
      <MemoryRouter initialEntries={['/login?role=admin']}>
        <Routes>
          <Route path="/login" element={<Login onLogin={mockOnLogin} />} />
        </Routes>
      </MemoryRouter>
    )

    // Verify it says Team Member -> Admin in badge
    expect(screen.getByText('Admin')).toBeInTheDocument()

    fireEvent.change(screen.getByPlaceholderText('Enter your username'), { target: { value: 'adminuser' } })
    fireEvent.change(screen.getByPlaceholderText('Enter your password'), { target: { value: 'adminpass' } })
    fireEvent.click(screen.getByRole('button', { name: /Login/i }))

    await waitFor(() => {
      expect(authAPI.adminLogin).toHaveBeenCalledWith({ username: 'adminuser', password: 'adminpass' })
    })

    expect(mockOnLogin).toHaveBeenCalledWith(expect.objectContaining({
      username: 'adminuser',
      role: 'admin'
    }))
  })
})
