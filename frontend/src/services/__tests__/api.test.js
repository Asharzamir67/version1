import { vi, describe, it, expect, beforeEach } from 'vitest'
import axios from 'axios'
import { authAPI, imageAPI } from '../api'

// Mock axios globally
vi.mock('axios', () => {
  const mockAxiosInstance = {
    post: vi.fn().mockResolvedValue({ data: {} }),
    get: vi.fn().mockResolvedValue({ data: {} }),
    put: vi.fn().mockResolvedValue({ data: {} }),
    delete: vi.fn().mockResolvedValue({ data: {} }),
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
    create: vi.fn(function() { return this })
  }
  return {
    default: mockAxiosInstance
  }
})

describe('API Services', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('authAPI', () => {
    it('should call login with correct parameters', async () => {
      const loginData = { username: 'test', password: 'password' }
      await authAPI.login(loginData)
      expect(axios.post).toHaveBeenCalledWith('/user/login', loginData)
    })
  })

  describe('imageAPI', () => {
    it('should call processImages with FormData', async () => {
      const mockImages = [new File([''], 'img1.jpg')]
      await imageAPI.processImages(mockImages, 'model', 'meta')
      
      expect(axios.post).toHaveBeenCalledWith(
        '/images/process',
        expect.any(FormData),
        expect.any(Object)
      )
    })
  })
})
