#!/usr/bin/env python3
"""
Test script for time validation functionality.
Creates a simple HTML page with time display and tests the time validator.
"""

import sys
import tempfile
from pathlib import Path
from datetime import datetime

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from monitoring.time_validator import TimeValidator
from playwright.sync_api import sync_playwright


def create_test_html_with_time(time_str: str) -> Path:
    """Create a test HTML file with a specific time display."""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Time Validation Test</title>
    </head>
    <body>
        <h1>Dashboard Test</h1>
        <div class="time">{time_str}</div>
        <p>This is a test page for time validation.</p>
    </body>
    </html>
    """
    
    # Create temporary HTML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(html_content)
        return Path(f.name)


def test_time_validation():
    """Test the time validation functionality."""
    print("🧪 Testing Time Validation Functionality")
    print("=" * 50)
    
    # Initialize time validator
    validator = TimeValidator()
    
    # Get current time for testing
    current_time = datetime.now()
    current_time_str = current_time.strftime("%I:%M %p").lstrip('0')
    
    # Test with correct time
    print(f"\n1. Testing with CORRECT time: {current_time_str}")
    test_html_correct = create_test_html_with_time(current_time_str)
    
    try:
        with open(test_html_correct, 'r') as f:
            html_content = f.read()
        
        result = validator.validate_time_from_html(html_content)
        validator.log_validation_summary(result)
        
        if result['success'] and not result.get('warning'):
            print("✅ PASSED: Correct time validation")
        else:
            print("❌ FAILED: Correct time validation should pass without warnings")
    finally:
        test_html_correct.unlink()
    
    # Test with incorrect time (5 minutes off)
    incorrect_time = current_time.replace(minute=(current_time.minute + 5) % 60)
    incorrect_time_str = incorrect_time.strftime("%I:%M %p").lstrip('0')
    
    print(f"\n2. Testing with INCORRECT time: {incorrect_time_str} (should be {current_time_str})")
    test_html_incorrect = create_test_html_with_time(incorrect_time_str)
    
    try:
        with open(test_html_incorrect, 'r') as f:
            html_content = f.read()
        
        result = validator.validate_time_from_html(html_content)
        validator.log_validation_summary(result)
        
        if result['success'] and result.get('warning'):
            print("✅ PASSED: Incorrect time validation detected mismatch")
        else:
            print("❌ FAILED: Incorrect time validation should detect mismatch")
    finally:
        test_html_incorrect.unlink()
    
    # Test with no time display
    print(f"\n3. Testing with NO time display")
    test_html_no_time = create_test_html_with_time("")
    
    try:
        with open(test_html_no_time, 'r') as f:
            html_content = f.read()
        
        result = validator.validate_time_from_html(html_content)
        validator.log_validation_summary(result)
        
        if result['success'] and 'No time displays found' in result.get('warning', ''):
            print("✅ PASSED: No time display handled correctly")
        else:
            print("❌ FAILED: No time display should be handled gracefully")
    finally:
        test_html_no_time.unlink()
    
    print("\n" + "=" * 50)
    print("🏁 Time validation tests completed!")


if __name__ == '__main__':
    test_time_validation()
