#!/usr/bin/env python3
"""
Test script for persistent browser functionality.
"""

import sys
import time
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# pylint: disable=wrong-import-position
from config.settings import Settings
from dashboard.renderer import DashboardRenderer


def test_persistent_browser():
    """Test the persistent browser functionality."""
    print("Testing persistent browser functionality...")
    
    # Create settings and load .env file
    settings = Settings()
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        settings.load_from_file(env_file)
        print(f"✅ Loaded configuration from {env_file}")
    else:
        print(f"⚠️  No .env file found at {env_file}")
    
    renderer = DashboardRenderer(settings)
    
    # Check if we have a DAKboard URL configured
    if not settings.dakboard_url:
        print("❌ No DAKboard URL configured. Please set DAKBOARD_URL in your .env file.")
        return False
    
    print(f"Using DAKboard URL: {settings.dakboard_url}")
    
    try:
        # Test 1: Start persistent browser
        print("\n1. Starting persistent browser...")
        start_time = time.time()
        success = renderer.start_persistent_browser(settings.dakboard_url)
        start_duration = time.time() - start_time
        
        if success:
            print(f"✅ Persistent browser started successfully in {start_duration:.1f}s")
        else:
            print("❌ Failed to start persistent browser")
            return False
        
        # Test 2: Take first screenshot
        print("\n2. Taking first screenshot...")
        screenshot_time = time.time()
        image1 = renderer.render_persistent_screenshot()
        screenshot_duration = time.time() - screenshot_time
        
        if image1:
            print(f"✅ First screenshot taken successfully in {screenshot_duration:.1f}s")
            print(f"   Image size: {image1.size}")
        else:
            print("❌ Failed to take first screenshot")
            return False
        
        # Test 3: Take second screenshot (should be faster)
        print("\n3. Taking second screenshot...")
        screenshot_time = time.time()
        image2 = renderer.render_persistent_screenshot()
        screenshot_duration = time.time() - screenshot_time
        
        if image2:
            print(f"✅ Second screenshot taken successfully in {screenshot_duration:.1f}s")
            print(f"   Image size: {image2.size}")
        else:
            print("❌ Failed to take second screenshot")
            return False
        
        # Test 4: Refresh browser page
        print("\n4. Testing browser page refresh...")
        refresh_success = renderer.refresh_persistent_browser()
        
        if refresh_success:
            print("✅ Browser page refreshed successfully")
        else:
            print("❌ Failed to refresh browser page")
            return False
        
        # Test 5: Take screenshot after refresh
        print("\n5. Taking screenshot after refresh...")
        screenshot_time = time.time()
        image3 = renderer.render_persistent_screenshot()
        screenshot_duration = time.time() - screenshot_time
        
        if image3:
            print(f"✅ Screenshot after refresh taken successfully in {screenshot_duration:.1f}s")
            print(f"   Image size: {image3.size}")
        else:
            print("❌ Failed to take screenshot after refresh")
            return False
        
        print("\n✅ All persistent browser tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
        
    finally:
        # Clean up
        print("\n6. Cleaning up...")
        try:
            renderer.cleanup_persistent_browser()
            print("✅ Cleanup completed")
        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")


def test_fallback_rendering():
    """Test fallback to standard rendering."""
    print("\n" + "="*50)
    print("Testing fallback rendering...")
    
    # Create settings and load .env file
    settings = Settings()
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        settings.load_from_file(env_file)
        print(f"✅ Loaded configuration from {env_file}")
    else:
        print(f"⚠️  No .env file found at {env_file}")
    
    renderer = DashboardRenderer(settings)
    
    if not settings.dakboard_url:
        print("❌ No DAKboard URL configured for fallback test.")
        return False
    
    try:
        print("Taking screenshot using standard rendering...")
        start_time = time.time()
        image = renderer._run_chromium(settings.dakboard_url, settings.browser_timeout)
        duration = time.time() - start_time
        
        if image:
            print(f"✅ Standard rendering successful in {duration:.1f}s")
            print(f"   Image size: {image.size}")
            return True
        else:
            print("❌ Standard rendering failed")
            return False
            
    except Exception as e:
        print(f"❌ Standard rendering failed with error: {e}")
        return False


if __name__ == "__main__":
    print("Pi Home Dashboard - Persistent Browser Test")
    print("=" * 50)
    
    # Test persistent browser
    persistent_success = test_persistent_browser()
    
    # Test fallback rendering
    fallback_success = test_fallback_rendering()
    
    print("\n" + "="*50)
    print("TEST SUMMARY:")
    print(f"Persistent Browser: {'✅ PASS' if persistent_success else '❌ FAIL'}")
    print(f"Fallback Rendering: {'✅ PASS' if fallback_success else '❌ FAIL'}")
    
    if persistent_success and fallback_success:
        print("\n🎉 All tests passed! The persistent browser implementation is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the error messages above.")
        sys.exit(1)
