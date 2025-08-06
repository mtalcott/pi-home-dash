#!/usr/bin/env python3
"""
Test script to verify the Pi Home Dashboard setup.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        from config.settings import Settings
        print("✓ Settings import successful")
    except ImportError as e:
        print(f"✗ Settings import failed: {e}")
        return False
    
    try:
        from dashboard.renderer import DashboardRenderer
        print("✓ DashboardRenderer import successful")
    except ImportError as e:
        print(f"✗ DashboardRenderer import failed: {e}")
        return False
    
    try:
        from display.eink_driver import EInkDriver
        print("✓ EInkDriver import successful")
    except ImportError as e:
        print(f"✗ EInkDriver import failed: {e}")
        return False
    
    return True

def test_configuration():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from config.settings import Settings
        settings = Settings()
        print(f"✓ Settings loaded - Display: {settings.display_width}x{settings.display_height}")
        print(f"✓ EPD Device: {settings.epd_device}")
        print(f"✓ EPD Mode: {settings.epd_mode}")
        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def test_display_driver():
    """Test display driver initialization."""
    print("\nTesting display driver...")
    
    try:
        from config.settings import Settings
        from display.eink_driver import EInkDriver
        
        settings = Settings()
        driver = EInkDriver(settings)
        
        print(f"✓ Display driver initialized")
        print(f"✓ Hardware available: {driver.is_available}")
        print(f"✓ Display size: {driver.width}x{driver.height}")
        
        return True
    except Exception as e:
        print(f"✗ Display driver test failed: {e}")
        return False

def test_omni_epd():
    """Test omni-epd library availability."""
    print("\nTesting omni-epd library...")
    
    try:
        from omni_epd import displayfactory
        print("✓ omni-epd library available")
        
        # Test mock display
        mock_display = displayfactory.load_display_driver("omni_epd.mock")
        if mock_display:
            print("✓ Mock display driver loaded successfully")
            print(f"✓ Mock display size: {mock_display.width}x{mock_display.height}")
        else:
            print("✗ Mock display driver failed to load")
            return False
            
        return True
    except ImportError:
        print("✗ omni-epd library not available")
        return False
    except Exception as e:
        print(f"✗ omni-epd test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Pi Home Dashboard - Setup Test")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_configuration,
        test_display_driver,
        test_omni_epd
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 40)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed! Setup is working correctly.")
        return 0
    else:
        print("✗ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
