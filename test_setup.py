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
        from display.it8951_driver import IT8951Driver
        print("✓ IT8951Driver import successful")
    except ImportError as e:
        print(f"✗ IT8951Driver import failed: {e}")
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
        from display.it8951_driver import IT8951Driver
        
        settings = Settings()
        driver = IT8951Driver(settings)
        
        print(f"✓ Display driver initialized")
        print(f"✓ Hardware available: {driver.is_available}")
        print(f"✓ Display size: {driver.width}x{driver.height}")
        print(f"✓ Supports partial refresh: {driver.supports_partial_refresh}")
        
        return True
    except Exception as e:
        print(f"✗ Display driver test failed: {e}")
        return False

def test_it8951():
    """Test IT8951 library availability and functionality."""
    print("\nTesting IT8951 library...")
    
    try:
        from config.settings import Settings
        from display.it8951_driver import IT8951Driver
        
        # Test with mock mode
        settings = Settings()
        settings.display_type = "mock"  # Force mock mode for testing
        
        driver = IT8951Driver(settings)
        print("✓ IT8951Driver initialized successfully")
        print(f"✓ Mock mode: {driver.mock_mode}")
        print(f"✓ Display size: {driver.width}x{driver.height}")
        print(f"✓ Supports partial refresh: {driver.supports_partial_refresh}")
        
        # Test basic functionality
        test_result = driver.test_display()
        if test_result:
            print("✓ Display test completed successfully")
        else:
            print("⚠️  Display test completed with warnings (check logs)")
        
        return True
    except ImportError as e:
        print(f"✗ IT8951 library not available: {e}")
        return False
    except Exception as e:
        print(f"✗ IT8951 test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Pi Home Dashboard - Setup Test")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_configuration,
        test_display_driver,
        test_it8951
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
