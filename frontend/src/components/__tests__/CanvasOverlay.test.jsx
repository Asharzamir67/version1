import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import CanvasOverlay from '../CanvasOverlay';
import React from 'react';

// Mock the canvas context
HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue({
  clearRect: vi.fn(),
  beginPath: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  stroke: vi.fn(),
  fill: vi.fn(),
  closePath: vi.fn(),
  strokeRect: vi.fn(),
  fillRect: vi.fn(),
  fillText: vi.fn(),
  strokeStyle: '',
  fillStyle: '',
  lineWidth: 1,
  font: ''
});

describe('CanvasOverlay Component', () => {
  const mockPredictions = [
    {
      box: [100, 100, 200, 200],
      conf: 0.95,
      class: 0,
      name: 'sealant',
      segments: {
        xyn: [[0.1, 0.1], [0.2, 0.1], [0.2, 0.2], [0.1, 0.2]]
      }
    }
  ];

  it('renders a canvas element', () => {
    const { container } = render(
      <CanvasOverlay 
        predictions={mockPredictions} 
        width={640} 
        height={480} 
      />
    );
    const canvas = container.querySelector('canvas');
    expect(canvas).toBeInTheDocument();
    expect(canvas).toHaveAttribute('width', '640');
    expect(canvas).toHaveAttribute('height', '480');
  });

  it('handles empty predictions gracefully', () => {
    const { container } = render(
      <CanvasOverlay 
        predictions={[]} 
        width={640} 
        height={480} 
      />
    );
    const canvas = container.querySelector('canvas');
    expect(canvas).toBeInTheDocument();
  });
});
