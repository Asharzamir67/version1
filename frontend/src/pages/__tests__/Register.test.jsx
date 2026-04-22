import { vi, describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import Register from '../Register'
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
    register: vi.fn(),
    adminRegister: vi.fn()
  }
}))

describe('Register Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render registration form for worker', () => {
    render(
      <MemoryRouter initialEntries={['/register?role=worker']}>
        <Routes>
          <Route path="/register" element={<Register />} />
        </Routes>
      </MemoryRouter>
    )
    expect(screen.getByText('Register as Team Member')).toBeInTheDocument()
    expect(screen.getByLabelText(/Username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument()
  })

  it('should render registration form for admin', () => {
    render(
      <MemoryRouter initialEntries={['/register?role=admin']}>
        <Routes>
          <Route path="/register" element={<Register />} />
        </Routes>
      </MemoryRouter>
    )
    expect(screen.getByText('Register as Admin')).toBeInTheDocument()
  })

  it('should call authAPI.register on worker registration', async () => {
    authAPI.register.mockResolvedValueOnce({ data: { success: true } })

    render(
      <MemoryRouter initialEntries={['/register?role=worker']}>
        <Routes>
          <Route path="/register" element={<Register />} />
        </Routes>
      </MemoryRouter>
    )

    fireEvent.change(screen.getByLabelText(/Username/i), { target: { value: 'newworker' } })
    fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: 'password123' } })
    fireEvent.click(screen.getByRole('button', { name: /Register/i }))

    await waitFor(() => {
      expect(authAPI.register).toHaveBeenCalledWith({
        username: 'newworker',
        password: 'password123'
      })
      expect(mockedUsedNavigate).toHaveBeenCalledWith('/login?role=worker')
    })
  })

  it('should call authAPI.adminRegister on admin registration', async () => {
    authAPI.adminRegister.mockResolvedValueOnce({ data: { success: true } })

    render(
      <MemoryRouter initialEntries={['/register?role=admin']}>
        <Routes>
          <Route path="/register" element={<Register />} />
        </Routes>
      </MemoryRouter>
    )

    fireEvent.change(screen.getByLabelText(/Username/i), { target: { value: 'newadmin' } })
    fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: 'adminpass' } })
    fireEvent.click(screen.getByRole('button', { name: /Register/i }))

    await waitFor(() => {
      expect(authAPI.adminRegister).toHaveBeenCalledWith({
        username: 'newadmin',
        password: 'adminpass'
      })
      expect(mockedUsedNavigate).toHaveBeenCalledWith('/login?role=admin')
    })
  })

  it('should display error message on failed registration', async () => {
    authAPI.register.mockRejectedValueOnce({
      response: { data: { detail: 'User already exists' } }
    })

    render(
      <MemoryRouter initialEntries={['/register?role=worker']}>
        <Routes>
          <Route path="/register" element={<Register />} />
        </Routes>
      </MemoryRouter>
    )

    fireEvent.change(screen.getByLabelText(/Username/i), { target: { value: 'existing' } })
    fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: 'pass' } })
    fireEvent.click(screen.getByRole('button', { name: /Register/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('User already exists')
    })
  })
})
