#!/usr/bin/env python3
"""
Test script for Pi Home Dashboard monitoring implementation.
Verifies that the new statsd-based metrics collection works correctly.
"""

import socket
import sys
import time
import logging
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from monitoring.metrics_collector import MetricsCollector, PerformanceTimer

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_statsd_connection():
    """Test if we can connect to the local statsd server."""
    print("Testing statsd connection...")
    
    try:
        # Try to connect to the statsd port
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        
        # Send a test metric
        test_metric = "test.metric:1|c"
        sock.sendto(test_metric.encode(), ('localhost', 8125))
        sock.close()
        
        print("  ✓ Successfully sent test metric to statsd!")
        return True
        
    except Exception as e:
        print(f"  ⚠ Could not connect to statsd: {e}")
        print("  ⚠ This is expected if netdata is not running")
        return False


def test_metrics_collector():
    """Test the statsd-based metrics collector functionality."""
    print("Testing MetricsCollector with statsd...")
    
    try:
        # Initialize metrics collector (will connect to local statsd on port 8125)
        collector = MetricsCollector()
        print("  ✓ MetricsCollector initialized")
        
        # Test basic metrics recording
        collector.record_render_time(1500.5, 'persistent_browser')
        collector.record_render_success()
        print("  ✓ Render metrics recorded")
        
        collector.record_display_update_time(800.1, 'partial')
        collector.record_display_success()
        print("  ✓ Display metrics recorded")
        
        # Test dashboard update metrics
        collector.record_update_attempt()
        collector.record_update_success()
        print("  ✓ Update metrics recorded")
        
        # Test system metrics
        collector.send_system_metrics(
            cpu_temp=65.5,
            memory_usage=45.2,
            cpu_usage=23.1,
            disk_usage=78.9
        )
        print("  ✓ System metrics sent")
        
        # Test browser metrics
        collector.send_browser_metrics(
            browser_memory=150.5,
            browser_processes=3
        )
        print("  ✓ Browser metrics sent")
        
        # Test service status
        collector.send_service_status(
            service_running=True,
            display_connected=True,
            network_connected=True
        )
        print("  ✓ Service status sent")
        
        # Test update interval setting
        collector.set_update_interval(60)
        print("  ✓ Update interval set")
        
        # Get metrics summary
        summary = collector.get_metrics_summary()
        print(f"  ✓ Metrics summary: {summary}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error testing metrics collector: {e}")
        return False


def test_performance_timer():
    """Test the PerformanceTimer context manager."""
    print("Testing PerformanceTimer...")
    
    try:
        collector = MetricsCollector()
        
        # Test render timing
        with PerformanceTimer(collector, 'render', render_type='persistent_browser'):
            time.sleep(0.1)  # Simulate 100ms render time
        print("  ✓ Render timer test completed")
        
        # Test display update timing
        with PerformanceTimer(collector, 'display_update', refresh_type='partial'):
            time.sleep(0.05)  # Simulate 50ms display update
        print("  ✓ Display update timer test completed")
        
        # Test with exception handling
        try:
            with PerformanceTimer(collector, 'render', render_type='standard') as timer:
                time.sleep(0.02)  # Simulate 20ms before failure
                raise Exception("Simulated render failure")
        except Exception as e:
            duration = timer.get_duration_ms()
            print(f"  ✓ Exception handling test completed (took {duration:.2f}ms)")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error testing PerformanceTimer: {e}")
        return False


def test_statsd_import():
    """Test that the statsd library is available."""
    print("Testing statsd library import...")
    
    try:
        import statsd
        client = statsd.StatsClient('localhost', 8125, prefix='test')
        print("  ✓ statsd library imported successfully")
        return True
    except ImportError:
        print("  ✗ statsd library not available")
        print("  ✗ Install with: pip install statsd")
        return False
    except Exception as e:
        print(f"  ✗ Error with statsd library: {e}")
        return False


def test_netdata_statsd_config():
    """Test if netdata statsd configuration exists."""
    print("Testing netdata statsd configuration...")
    
    try:
        netdata_config = Path('/etc/netdata/netdata.conf')
        
        if not netdata_config.exists():
            print("  ⚠ Netdata config file not found")
            print("  ⚠ Run: sudo ./scripts/setup_monitoring.sh")
            return False
        
        with open(netdata_config, 'r') as f:
            content = f.read()
        
        if '[statsd]' in content:
            print("  ✓ Netdata statsd configuration found")
            return True
        else:
            print("  ⚠ Netdata statsd configuration not found")
            print("  ⚠ Run: sudo ./scripts/setup_monitoring.sh")
            return False
            
    except PermissionError:
        print("  ⚠ Cannot read netdata config (permission denied)")
        return False
    except Exception as e:
        print(f"  ✗ Error checking netdata config: {e}")
        return False


def test_metrics_integration():
    """Test end-to-end metrics integration."""
    print("Testing end-to-end metrics integration...")
    
    try:
        collector = MetricsCollector()
        
        # Simulate a complete dashboard update cycle
        collector.record_update_attempt()
        
        # Simulate render phase
        with PerformanceTimer(collector, 'render', render_type='persistent_browser'):
            time.sleep(0.05)  # 50ms render
        
        # Simulate display update phase
        with PerformanceTimer(collector, 'display_update', refresh_type='partial'):
            time.sleep(0.02)  # 20ms display update
        
        # Send system health metrics
        collector.send_system_metrics(cpu_temp=60.0, memory_usage=40.0)
        
        # Mark as successful
        collector.record_update_success()
        
        print("  ✓ Complete update cycle simulated")
        return True
        
    except Exception as e:
        print(f"  ✗ Error in integration test: {e}")
        return False


def main():
    """Run all monitoring tests."""
    print("Pi Home Dashboard Monitoring Test Suite (StatSD)")
    print("=" * 55)
    
    tests = [
        test_statsd_import,
        test_statsd_connection,
        test_metrics_collector,
        test_performance_timer,
        test_netdata_statsd_config,
        test_metrics_integration
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
    
    print("=" * 55)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All monitoring tests passed!")
        print("\nThe statsd-based metrics collector is working correctly.")
        print("\nNext steps:")
        print("1. Install statsd library: pip install statsd")
        print("2. Setup monitoring: sudo ./scripts/setup_monitoring.sh")
        print("3. Start netdata: sudo systemctl start netdata")
        print("4. Start dashboard: python src/main.py --continuous")
        print("5. View metrics: http://localhost:19999 (look for 'pi_dashboard' charts)")
        return 0
    else:
        print("❌ Some monitoring tests failed!")
        print("\nTroubleshooting:")
        if failed > 0:
            print("- Install statsd: pip install statsd")
            print("- Setup monitoring: sudo ./scripts/setup_monitoring.sh")
            print("- Start netdata: sudo systemctl start netdata")
        return 1


if __name__ == '__main__':
    sys.exit(main())
