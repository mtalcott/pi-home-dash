#!/usr/bin/env python3
"""
Pi Home Dashboard - Main Application Entry Point

A smart calendar dashboard for e-ink displays powered by Raspberry Pi Zero 2 W.
Renders calendar, weather, and to-do information to a Waveshare 10.3" e-Paper display.
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import Settings
from dashboard.renderer import DashboardRenderer
from dashboard.mock_renderer import MockDashboardRenderer
from display.it8951_driver import IT8951Driver
from monitoring.prometheus_collector import PrometheusCollector, PrometheusTimer


class PiHomeDashboard:
    """Main dashboard application class."""
    
    def __init__(self, test_mode=False):
        """Initialize the dashboard application."""
        self.settings = Settings()
        self.test_mode = test_mode
        
        # Initialize renderer (mock or real based on settings)
        if self.settings.dashboard_type == 'mock' or test_mode:
            self.renderer = MockDashboardRenderer(self.settings)
        else:
            self.renderer = DashboardRenderer(self.settings)
        
        # Initialize display driver (IT8951 or mock based on settings)
        # IT8951Driver handles mock mode internally based on settings.display_type
        self.display = IT8951Driver(self.settings)
        
        # Initialize metrics collection
        self.metrics = PrometheusCollector(port=self.settings.prometheus_port)
        if self.settings.prometheus_enabled:
            self.metrics.start_server()
        self.metrics.set_update_interval(self.settings.update_interval)
        
        # Persistent browser state
        self.persistent_browser_enabled = False
        self.browser_refresh_count = 0
        self.max_renders_before_refresh = 1440  # Refresh browser every day (1440 minutes)
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Log initialization info
        if test_mode:
            self.logger.info("Dashboard initialized in test mode")
        
        renderer_type = "Mock" if isinstance(self.renderer, MockDashboardRenderer) and self.renderer.is_mock_mode() else "Standard"
        display_type = "Mock" if hasattr(self.display, 'mock_mode') and self.display.mock_mode else "Hardware"
        self.logger.info(f"Renderer: {renderer_type}, Display: {display_type}")
        
    def _setup_logging(self):
        """Configure logging based on settings."""
        level = logging.DEBUG if self.settings.debug_mode else logging.INFO
        
        # Setup handlers
        handlers = [logging.StreamHandler(sys.stdout)]
        
        # Try to add file handler, fall back gracefully if permissions denied
        try:
            handlers.append(logging.FileHandler('/var/log/pi-dashboard.log'))
        except PermissionError:
            # Fall back to local log file
            try:
                log_file = self.settings.project_root / 'logs' / 'pi-dashboard.log'
                log_file.parent.mkdir(exist_ok=True)
                handlers.append(logging.FileHandler(str(log_file)))
            except Exception:
                # If all else fails, just use console logging
                pass
        
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
    
    def _initialize_persistent_browser_with_retry(self, max_retries=3, retry_delay=5):
        """Initialize persistent browser with retry logic."""
        for attempt in range(1, max_retries + 1):
            self.logger.info(f"Persistent browser initialization attempt {attempt}/{max_retries}")
            
            try:
                success = self.renderer.start_persistent_browser(self.settings.dakboard_url)
                if success:
                    self.logger.info(f"Persistent browser initialized successfully on attempt {attempt}")
                    return True
                else:
                    self.logger.warning(f"Attempt {attempt} failed to initialize persistent browser")
                    
            except Exception as e:
                self.logger.error(f"Attempt {attempt} failed with exception: {e}")
            
            # Wait before retrying (except on the last attempt)
            if attempt < max_retries:
                self.logger.info(f"Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
        
        self.logger.error(f"Failed to initialize persistent browser after {max_retries} attempts")
        return False
    
    def _wait_until_top_of_minute(self, target_second=0):
        """Wait until the specified second of the next minute.
        
        Args:
            target_second: Target second within the minute (0-59). Default is 0 for top of minute.
        """
        now = datetime.now()
        current_second = now.second
        current_microsecond = now.microsecond
        
        # Calculate seconds until target
        if current_second <= target_second:
            # We're before the target second in the current minute
            seconds_to_wait = target_second - current_second
        else:
            # We're past the target second, wait until target second of next minute
            seconds_to_wait = (60 - current_second) + target_second
        
        # Subtract the microseconds to be more precise
        seconds_to_wait -= current_microsecond / 1_000_000
        
        if seconds_to_wait > 0:
            self.logger.info(f"Waiting {seconds_to_wait:.2f} seconds until :{target_second:02d} of the minute...")
            time.sleep(seconds_to_wait)
        
        # Log the actual time we're taking the screenshot
        actual_time = datetime.now()
        self.logger.info(f"Taking screenshot at {actual_time.strftime('%H:%M:%S.%f')[:-3]}")
    
    def _save_persistent_screenshot(self, image, timestamp=None):
        """Save a persistent screenshot with timestamp.
        
        Args:
            image: PIL Image to save
            timestamp: Optional datetime object. If None, uses current time.
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Create screenshots directory if it doesn't exist
        screenshots_dir = self.settings.project_root / "screenshots"
        screenshots_dir.mkdir(exist_ok=True)
        
        # Generate filename with timestamp
        filename = f"dashboard_{timestamp.strftime('%Y%m%d_%H%M%S')}.png"
        filepath = screenshots_dir / filename
        
        try:
            image.save(filepath, "PNG")
            self.logger.info(f"Persistent screenshot saved: {filepath}")
            
            # Also save as "latest.png" for easy access
            latest_path = screenshots_dir / "latest.png"
            image.save(latest_path, "PNG")
            
            return filepath
        except Exception as e:
            self.logger.error(f"Failed to save persistent screenshot: {e}")
            return None
    
    def update_display(self, force_full_refresh=False):
        """Update the e-ink display with current dashboard content."""
        # Record update attempt
        self.metrics.record_update_attempt()
        
        # Determine render and refresh types for metrics
        refresh_type = 'full' if force_full_refresh else 'partial'
        render_type = 'persistent_browser' if (self.settings.dashboard_type == "dakboard" and 
                                             self.persistent_browser_enabled) else 'standard'
        
        try:
            self.logger.info("Starting display update...")
            
            # Wrap the entire render+display cycle with full cycle timing
            with PrometheusTimer(self.metrics, 'full_cycle', render_type=render_type, refresh_type=refresh_type):
                
                # Initialize persistent browser if needed for DAKboard
                if (self.settings.dashboard_type == "dakboard" and 
                    not self.persistent_browser_enabled and 
                    self.settings.dakboard_url):
                    
                    self.logger.info("Initializing persistent browser for DAKboard...")
                    success = self._initialize_persistent_browser_with_retry()
                    if success:
                        self.persistent_browser_enabled = True
                        self.browser_refresh_count = 0
                        self.logger.info("Persistent browser initialized successfully")
                        # Update render type now that persistent browser is enabled
                        render_type = 'persistent_browser'
                    else:
                        self.logger.error("Failed to initialize persistent browser after retries")
                        return False
                
                # Render dashboard content with performance timing
                self.logger.info("Rendering dashboard content...")
                dashboard_image = None
                
                # Use persistent browser for DAKboard if available
                if (self.settings.dashboard_type == "dakboard" and 
                    self.persistent_browser_enabled):
                    
                    # Check if we need to refresh the browser page
                    if self.browser_refresh_count >= self.max_renders_before_refresh:
                        self.logger.info("Refreshing persistent browser page...")
                        refresh_success = self.renderer.refresh_persistent_browser()
                        if refresh_success:
                            self.browser_refresh_count = 0
                            self.logger.info("Browser page refreshed successfully")
                        else:
                            self.logger.warning("Failed to refresh browser page")
                    
                    # Take screenshot using persistent browser with timing
                    with PrometheusTimer(self.metrics, 'render', render_type='persistent_browser'):
                        dashboard_image = self.renderer.render_persistent_screenshot()
                        self.browser_refresh_count += 1
                    
                    # If screenshot fails, retry persistent browser initialization
                    if dashboard_image is None:
                        self.logger.warning("Persistent browser screenshot failed, retrying initialization...")
                        self.persistent_browser_enabled = False
                        success = self._initialize_persistent_browser_with_retry()
                        if success:
                            self.persistent_browser_enabled = True
                            self.browser_refresh_count = 0
                            # Try screenshot again with newly initialized browser
                            with PrometheusTimer(self.metrics, 'render', render_type='persistent_browser'):
                                dashboard_image = self.renderer.render_persistent_screenshot()
                                self.browser_refresh_count += 1
                        
                        if dashboard_image is None:
                            self.logger.error("Failed to render dashboard after persistent browser retry")
                            self.metrics.record_update_failure()
                            return False
                else:
                    # Use standard rendering for non-DAKboard or when persistent browser is not available
                    with PrometheusTimer(self.metrics, 'render', render_type='standard'):
                        dashboard_image = self.renderer.render()
                
                if dashboard_image is None:
                    self.logger.error("Failed to render dashboard content")
                    self.metrics.record_update_failure()
                    return False
                
                # Update display with performance timing
                self.logger.info("Updating e-ink display...")
                
                with PrometheusTimer(self.metrics, 'display_update', refresh_type=refresh_type):
                    success = self.display.update(dashboard_image, force_full_refresh)
                
                if success:
                    self.logger.info("Display update completed successfully")
                    self.metrics.record_update_success()
                    
                    # Log performance summary periodically (simplified for Prometheus)
                    summary = self.metrics.get_metrics_summary()
                    self.logger.info(f"Performance summary: {summary}")
                else:
                    self.logger.error("Display update failed")
                    self.metrics.record_update_failure()
                    
                return success
            
        except Exception as e:
            self.logger.error(f"Error during display update: {e}")
            self.metrics.record_update_failure()
            return False
    
    def test_display(self):
        """Test the display with a sample image."""
        try:
            self.logger.info("Running display test...")
            
            # Use the display's built-in test method
            success = self.display.test_display()
            
            if success:
                self.logger.info("Display test completed successfully")
            else:
                self.logger.error("Display test failed")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error during display test: {e}")
            return False
    
    def run_continuous(self):
        """Run the dashboard in continuous mode with periodic updates."""
        self.logger.info("Starting continuous dashboard mode with top-of-minute timing...")
        
        # Initial display update
        self.update_display(force_full_refresh=True)
        
        try:
            while True:
                # Wait until close to the top of the next minute
                self._wait_until_top_of_minute(target_second=0)
                
                # Calculate the next intended update time BEFORE starting the render process
                # This ensures consistent timing regardless of processing duration
                current_time = datetime.now()
                if self.settings.update_interval < 60:
                    # For sub-minute intervals, next update is at the next minute boundary
                    next_update_time = current_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
                else:
                    # For intervals >= 60 seconds, next update is current time + interval
                    next_update_time = current_time + timedelta(seconds=self.settings.update_interval)
                
                self.logger.info(f"Next update scheduled for: {next_update_time.strftime('%H:%M:%S')}")
                
                # Update display - let the eink_driver handle full vs partial refresh logic
                # based on the partial refresh count
                success = self.update_display(force_full_refresh=False)
                
                # Record timing offset metric after display update completes
                actual_completion_time = datetime.now()
                timing_offset_seconds = (actual_completion_time - next_update_time).total_seconds()
                self.metrics.record_update_timing_offset(timing_offset_seconds)
                
                # Calculate remaining time until next intended update
                time_until_next_update = (next_update_time - actual_completion_time).total_seconds()
                
                # Only sleep if there's time remaining (avoid negative sleep)
                if time_until_next_update > 0:
                    self.logger.info(f"Update completed, waiting {time_until_next_update:.2f} seconds until next update...")
                    time.sleep(time_until_next_update)
                else:
                    self.logger.warning(f"Update took longer than expected, next update is {abs(time_until_next_update):.2f} seconds overdue")
                
        except KeyboardInterrupt:
            self.logger.info("Dashboard stopped by user")
        except Exception as e:
            self.logger.error(f"Error in continuous mode: {e}")
    
    def cleanup(self):
        """Clean up resources."""
        try:
            # Clean up persistent browser if running
            if self.persistent_browser_enabled:
                self.logger.info("Cleaning up persistent browser...")
                self.renderer.cleanup_persistent_browser()
                self.persistent_browser_enabled = False
            
            # Clean up display
            self.display.cleanup()
            self.logger.info("Cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Pi Home Dashboard')
    parser.add_argument('--update', action='store_true', 
                       help='Update display once and exit')
    parser.add_argument('--test', action='store_true',
                       help='Test display with sample image')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    parser.add_argument('--continuous', action='store_true',
                       help='Run in continuous mode (default)')
    parser.add_argument('--integration-test', action='store_true',
                       help='Run integration test with HTML rendering and virtual display')
    parser.add_argument('--duration', type=int, default=60,
                       help='Test duration in seconds (default: 60)')
    parser.add_argument('--interval', type=int, default=3,
                       help='Test update interval in seconds (default: 3)')
    parser.add_argument('--partial-refresh', action='store_true',
                       help='Test partial refresh functionality')
    parser.add_argument('--collect-artifacts', action='store_true',
                       help='Collect and validate test artifacts during tests')
    
    args = parser.parse_args()
    
    # Create dashboard instance
    dashboard = PiHomeDashboard()
    
    # Override debug setting if specified
    if args.debug:
        dashboard.settings.debug_mode = True
        dashboard._setup_logging()
    
    try:
        if args.integration_test:
            # Integration test mode
            from test.integration_test import run_integration_test
            results = run_integration_test(
                duration=args.duration,
                interval=args.interval,
                collect_artifacts=args.collect_artifacts
            )
            success = results.get('success', False)
            if success:
                print(f"\n✅ Integration test PASSED")
                if 'validation' in results and results['validation']['overall_pass']:
                    print("✅ All validation criteria met")
                else:
                    print("⚠️  Some validation criteria not met - check reports")
            else:
                print(f"\n❌ Integration test FAILED: {results.get('error', 'Unknown error')}")
            sys.exit(0 if success else 1)
            
        elif args.partial_refresh:
            # Partial refresh test mode
            dashboard.logger.info("Running partial refresh test...")
            
            # Test multiple partial refreshes followed by full refresh
            for i in range(5):
                dashboard.logger.info(f"Partial refresh test {i+1}/5")
                success = dashboard.update_display(force_full_refresh=False)
                if not success:
                    print(f"❌ Partial refresh test failed at iteration {i+1}")
                    sys.exit(1)
                time.sleep(2)
            
            # Final full refresh
            dashboard.logger.info("Testing full refresh after partial refreshes")
            success = dashboard.update_display(force_full_refresh=True)
            
            if success:
                print("✅ Partial refresh test PASSED")
                # Print refresh statistics
                if hasattr(dashboard.display, 'get_refresh_stats'):
                    stats = dashboard.display.get_refresh_stats()
                    print(f"Refresh stats: {stats}")
            else:
                print("❌ Partial refresh test FAILED")
            
            sys.exit(0 if success else 1)
            
        elif args.test:
            # Test mode
            success = dashboard.test_display()
            sys.exit(0 if success else 1)
            
        elif args.update:
            # Single update mode
            success = dashboard.update_display(force_full_refresh=True)
            sys.exit(0 if success else 1)
            
        else:
            # Continuous mode (default)
            dashboard.run_continuous()
            
    except Exception as e:
        logging.error(f"Unhandled error: {e}")
        sys.exit(1)
        
    finally:
        dashboard.cleanup()


if __name__ == '__main__':
    main()
