#!/usr/bin/env python3
"""
Test script for Pi Home Dashboard monitoring implementation.
Verifies that metrics collection and netdata integration work correctly.
"""

import json
import sys
import time
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config.settings import Settings
from monitoring.metrics_collector import MetricsCollector, PerformanceTimer


def test_metrics_collector():
    """Test the metrics collector functionality."""
    print("Testing MetricsCollector...")
    
    # Create test settings
    settings = Settings()
    
    # Initialize metrics collector
    metrics = MetricsCollector(settings.cache_dir)
    
    # Test basic functionality
    print("  ✓ MetricsCollector initialized")
    
    # Test recording metrics
    metrics.record_render_time(1500.0, 'persistent_browser')
    metrics.record_render_time(3000.0, 'standard')
    metrics.record_display_update_time(500.0, 'partial')
    metrics.record_display_update_time(2000.0, 'full')
    
    print("  ✓ Metrics recorded successfully")
    
    # Test metrics retrieval
    avg_render = metrics.get_average_render_time()
    avg_display = metrics.get_average_display_time()
    success_rate = metrics.get_success_rate()
    
    print(f"  ✓ Average render time: {avg_render:.1f}ms")
    print(f"  ✓ Average display time: {avg_display:.1f}ms")
    print(f"  ✓ Success rate: {success_rate:.1f}%")
    
    # Test metrics summary
    summary = metrics.get_metrics_summary()
    print("  ✓ Metrics summary generated")
    
    return True


def test_performance_timer():
    """Test the performance timer context manager."""
    print("Testing PerformanceTimer...")
    
    settings = Settings()
    metrics = MetricsCollector(settings.cache_dir)
    
    # Test render timing
    with PerformanceTimer(metrics, 'render', render_type='persistent_browser') as timer:
        time.sleep(0.1)  # Simulate render time
    
    duration = timer.get_duration_ms()
    print(f"  ✓ Render timer recorded: {duration:.1f}ms")
    
    # Test display timing
    with PerformanceTimer(metrics, 'display_update', refresh_type='partial') as timer:
        time.sleep(0.05)  # Simulate display update
    
    duration = timer.get_duration_ms()
    print(f"  ✓ Display timer recorded: {duration:.1f}ms")
    
    return True


def test_metrics_persistence():
    """Test that metrics are properly saved and loaded."""
    print("Testing metrics persistence...")
    
    settings = Settings()
    
    # Create first metrics instance and record data
    metrics1 = MetricsCollector(settings.cache_dir)
    metrics1.record_render_time(1000.0, 'standard')
    metrics1.record_update_attempt()
    metrics1.record_update_success()
    
    # Create second metrics instance and verify data persists
    metrics2 = MetricsCollector(settings.cache_dir)
    
    if metrics2.get_average_render_time() > 0:
        print("  ✓ Metrics persistence working")
        return True
    else:
        print("  ✗ Metrics persistence failed")
        return False


def test_netdata_collector():
    """Test the netdata collector (basic import and structure)."""
    print("Testing netdata collector...")
    
    try:
        # Import the collector module
        collector_path = Path(__file__).parent / 'monitoring' / 'collectors' / 'pi_dashboard.py'
        
        if not collector_path.exists():
            print("  ✗ Collector file not found")
            return False
        
        # Read and basic syntax check
        with open(collector_path, 'r') as f:
            content = f.read()
        
        # Check for required components
        required_components = [
            'class PiDashboardCollector',
            'def update(self, interval)',
            'def check(self)',
            'SERVICE = PiDashboardCollector'
        ]
        
        for component in required_components:
            if component not in content:
                print(f"  ✗ Missing required component: {component}")
                return False
        
        print("  ✓ Netdata collector structure valid")
        return True
        
    except Exception as e:
        print(f"  ✗ Error testing netdata collector: {e}")
        return False


def test_metrics_file_format():
    """Test that the metrics file format is valid JSON."""
    print("Testing metrics file format...")
    
    settings = Settings()
    metrics = MetricsCollector(settings.cache_dir)
    
    # Record some test data
    metrics.record_render_time(1500.0)
    metrics.record_display_update_time(800.0)
    
    # Check if metrics file exists and is valid JSON
    metrics_file = settings.cache_dir / 'metrics.json'
    
    if not metrics_file.exists():
        print("  ✗ Metrics file not created")
        return False
    
    try:
        with open(metrics_file, 'r') as f:
            data = json.load(f)
        
        # Check for required fields
        required_fields = [
            'render_times', 'display_update_times', 'total_attempts',
            'successful_attempts', 'last_updated'
        ]
        
        for field in required_fields:
            if field not in data:
                print(f"  ✗ Missing required field: {field}")
                return False
        
        print("  ✓ Metrics file format valid")
        return True
        
    except json.JSONDecodeError as e:
        print(f"  ✗ Invalid JSON in metrics file: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Error reading metrics file: {e}")
        return False


def main():
    """Run all monitoring tests."""
    print("Pi Home Dashboard Monitoring Test Suite")
    print("=" * 50)
    
    tests = [
        test_metrics_collector,
        test_performance_timer,
        test_metrics_persistence,
        test_netdata_collector,
        test_metrics_file_format
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ✗ Test failed with exception: {e}")
            failed += 1
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All monitoring tests passed!")
        print("\nNext steps:")
        print("1. Run: ./scripts/setup_monitoring.sh")
        print("2. Start the dashboard: python src/main.py --continuous")
        print("3. Access netdata at: http://localhost:19999")
        return 0
    else:
        print("❌ Some monitoring tests failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())
