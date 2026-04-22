import pytest
import numpy as np
from unittest.mock import MagicMock
from services.defect_detector import detect_defects

class MockResult:
    def __init__(self, mask_data=None):
        if mask_data is not None:
            self.masks = MagicMock()
            # Mock the .data.cpu().numpy() chain
            self.masks.data.cpu.return_value.numpy.return_value = mask_data
        else:
            self.masks = None

def test_detect_defects_empty_result():
    """Test when no masks are detected."""
    result = MockResult(mask_data=None)
    assert detect_defects(result) == "ng"

def test_detect_defects_zero_masks():
    """Test when masks list is empty."""
    result = MockResult(mask_data=np.array([]))
    assert detect_defects(result) == "ng"

def test_detect_defects_below_threshold():
    """Test coverage of 39% (should be ng)."""
    # Create a 100x100 mask grid
    mask = np.zeros((1, 100, 100))
    # Fill 3900 pixels (39%)
    mask[0, :39, :100] = 1
    result = MockResult(mask_data=mask)
    assert detect_defects(result) == "ng"

def test_detect_defects_at_threshold():
    """Test coverage of exactly 40% (should be ok)."""
    mask = np.zeros((1, 100, 100))
    mask[0, :40, :100] = 1
    result = MockResult(mask_data=mask)
    assert detect_defects(result) == "ok"

def test_detect_defects_above_threshold():
    """Test coverage of 80% (should be ok)."""
    mask = np.zeros((1, 100, 100))
    mask[0, :80, :100] = 1
    result = MockResult(mask_data=mask)
    assert detect_defects(result) == "ok"

def test_detect_defects_multiple_masks_overlapping():
    """Test that multiple masks are correctly combined using OR."""
    mask = np.zeros((2, 100, 100))
    # Mask 1 covers top 25%
    mask[0, :25, :] = 1
    # Mask 2 covers top-middle 25% (overlapping and extending)
    mask[1, 15:40, :] = 1
    # Total unique occupied rows: 0 to 40 -> 40%
    
    result = MockResult(mask_data=mask)
    assert detect_defects(result) == "ok"

def test_detect_defects_multiple_masks_disjoint():
    """Test that multiple disjoint masks are correctly summed."""
    mask = np.zeros((2, 100, 100))
    # Mask 1 covers 20%
    mask[0, :20, :] = 1
    # Mask 2 covers another 20% elsewhere
    mask[1, 50:70, :] = 1
    # Total unique occupied: 40%
    
    result = MockResult(mask_data=mask)
    assert detect_defects(result) == "ok"

def test_detect_defects_error_handling():
    """Test that it handles exceptions during mask access gracefully."""
    result = MagicMock()
    # Force an exception when accessing result.masks.data
    result.masks.data.cpu.side_effect = Exception("CUDA error")
    assert detect_defects(result) == "ng"
