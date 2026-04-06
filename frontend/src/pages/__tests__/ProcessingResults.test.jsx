import { vi, describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ProcessingResults from '../ProcessingResults'

const mockedUsedNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockedUsedNavigate,
    useLocation: vi.fn(() => ({ state: { result: mockResult } }))
  }
})

const mockResult = {
  status: 'good',
  model: 'yolo8n',
  images: [
    {
      filename: 'cam1.jpg',
      visualized: 'base64encodedstring',
      defect: 'good',
      predictions: { boxes: [{}] }
    }
  ]
}

import { useLocation } from 'react-router-dom'

describe('Processing Results Page', () => {
  it('should render results grid when result data is present', () => {
    render(
      <MemoryRouter>
        <ProcessingResults />
      </MemoryRouter>
    )

    expect(screen.getByText('Processing Results')).toBeInTheDocument()
    expect(screen.getByText('cam1.jpg')).toBeInTheDocument()
    expect(screen.getByText('GOOD')).toBeInTheDocument()
    expect(screen.getByText('Batch Status:')).toBeInTheDocument()
  })

  it('should render "No Results" state when location state is empty', () => {
    vi.mocked(useLocation).mockReturnValueOnce({ state: null })
    
    render(
      <MemoryRouter>
        <ProcessingResults />
      </MemoryRouter>
    )

    expect(screen.getByText('No Results')).toBeInTheDocument()
    expect(screen.getByText('No data available.')).toBeInTheDocument()
  })

  it('should navigate back to dashboard on button click', () => {
    render(
      <MemoryRouter>
        <ProcessingResults />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByText('Process Next Batch'))
    expect(mockedUsedNavigate).toHaveBeenCalledWith('/worker-dashboard')
  })
})
