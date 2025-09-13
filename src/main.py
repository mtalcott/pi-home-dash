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
import psutil
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
        
        # Initialize metrics collection first
        self.metrics = PrometheusCollector(port=self.settings.prometheus_port)
        if self.settings.prometheus_enabled:
            self.metrics.start_server()
        self.metrics.set_update_interval(self.settings.update_interval)
        
        # Initialize renderer (mock or real based on settings)
        if self.settings.dashboard_type == 'mock' or test_mode:
            self.renderer = MockDashboardRenderer(self.settings)
        else:
            self.renderer = DashboardRenderer(self.settings, self.metrics)
        
        # Initialize display driver (IT8951 or mock based on settings)
        # IT8951Driver handles mock mode internally based on settings.display_type
        self.display = IT8951Driver(self.settings)
        
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
    
    def _save_persistent_screenshot(self, image, timestamp=None):
        """Save a persistent screenshot with timestamp and manage screenshot limit.
        
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
            self.logger.info(f"Debug screenshot saved: {filepath}")
            
            # Also save as "latest.png" for easy access
            latest_path = screenshots_dir / "latest.png"
            image.save(latest_path, "PNG")
            
            # Manage screenshot limit (keep only the 10 most recent)
            self._cleanup_old_screenshots(screenshots_dir, max_screenshots=10)
            
            return filepath
        except Exception as e:
            self.logger.error(f"Failed to save debug screenshot: {e}")
            return None
    
    def _cleanup_old_screenshots(self, screenshots_dir, max_screenshots=10):
        """Remove old screenshots to maintain the specified limit.
        
        Args:
            screenshots_dir: Path to screenshots directory
            max_screenshots: Maximum number of screenshots to keep (default: 10)
        """
        try:
            # Get all dashboard screenshot files (exclude latest.png)
            screenshot_files = []
            for file_path in screenshots_dir.glob("dashboard_*.png"):
                if file_path.name != "latest.png":
                    screenshot_files.append(file_path)
            
            # Sort by modification time (newest first)
            screenshot_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Remove files beyond the limit
            files_to_remove = screenshot_files[max_screenshots:]
            for file_path in files_to_remove:
                try:
                    file_path.unlink()
                    self.logger.debug(f"Removed old screenshot: {file_path.name}")
                except Exception as e:
                    self.logger.warning(f"Failed to remove old screenshot {file_path.name}: {e}")
            
            if files_to_remove:
                self.logger.info(f"Cleaned up {len(files_to_remove)} old screenshots, keeping {min(len(screenshot_files), max_screenshots)} most recent")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old screenshots: {e}")
    
    def _get_friendly_timestamp(self):
        """Get a friendly formatted timestamp for display messages."""
        now = datetime.now()
        
        # Format: "Monday, January 15 at 2:30:45 PM"
        day_name = now.strftime("%A")
        month_name = now.strftime("%B")
        day = now.day
        
        time_str = now.strftime("%I:%M:%S %p")
        
        return f"{day_name}, {month_name} {day} at {time_str}"
    
    def _show_initializing_message(self):
        """Show initializing message with mode and friendly timestamp on the e-ink display."""
        friendly_time = self._get_friendly_timestamp()
        mode_display = self.settings.dashboard_type.title()
        
        # Log the initializing message
        self.logger.info(f"Initializing {mode_display} at {friendly_time}...")
        
        try:
            # Use the consolidated functionality from IT8951Driver
            success = self.display.display_initializing_message(mode_display, friendly_time)
            
            if success:
                self.logger.info("Initializing message displayed successfully")
            else:
                self.logger.warning("Failed to display initializing message")
                
        except Exception as e:
            self.logger.error(f"Error displaying initializing message: {e}")
            # Fall back to console message if display fails
            print(f"🚀 Initializing {mode_display} at {friendly_time}...")
    
    def _collect_browser_metrics(self):
        """Collect and send browser metrics to Prometheus."""
        try:
            browser_processes = 0
            browser_memory_mb = 0.0
            
            # Look for headless_shell processes (Playwright browser processes)
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info['name'].lower()
                    
                    # Check if this is a headless_shell process (Playwright browser)
                    if 'headless_shell' in proc_name:
                        browser_processes += 1
                        # Convert bytes to MB
                        memory_bytes = proc_info['memory_info'].rss
                        browser_memory_mb += memory_bytes / (1024 * 1024)
                        
                        self.logger.debug(f"Found browser process: {proc_info['name']} (PID: {proc_info['pid']}, Memory: {memory_bytes / (1024 * 1024):.1f}MB)")
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # Process disappeared or access denied, skip it
                    continue
            
            # Send browser metrics
            self.metrics.send_browser_metrics(
                browser_memory=browser_memory_mb,
                browser_processes=browser_processes
            )
            
            self.logger.debug(f"Browser metrics collected - Processes: {browser_processes}, Memory: {browser_memory_mb:.1f}MB")
            
        except Exception as e:
            self.logger.warning(f"Failed to collect browser metrics: {e}")
    
    def _calculate_next_update_time(self, current_time):
        """Calculate the next update time, aligning to minute boundaries for round minute intervals.
        For DAKboard mode, targets 5 seconds after the top of the minute to account for DAKboard loading delay.
        
        Args:
            current_time: datetime object representing the current time
            
        Returns:
            datetime object representing when the next update should occur
        """
        interval_seconds = self.settings.update_interval
        is_dakboard_mode = self.settings.dashboard_type == "dakboard"
        
        # Check if the interval is a round minute (60, 120, 300, etc.)
        if interval_seconds >= 60 and interval_seconds % 60 == 0:
            # For round minute intervals, align to the top of the minute
            interval_minutes = interval_seconds // 60
            
            # Get the next minute boundary
            next_minute = current_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
            
            # For intervals longer than 1 minute, find the next aligned time
            if interval_minutes > 1:
                # Calculate how many minutes past the hour we are
                minutes_past_hour = next_minute.minute
                
                # Find the next time that aligns with our interval
                # For example, with 5-minute intervals (300s), align to :00, :05, :10, etc.
                next_aligned_minute = ((minutes_past_hour // interval_minutes) + 1) * interval_minutes
                
                if next_aligned_minute >= 60:
                    # Roll over to the next hour
                    next_update_time = next_minute.replace(minute=0) + timedelta(hours=1, minutes=next_aligned_minute - 60)
                else:
                    next_update_time = next_minute.replace(minute=next_aligned_minute)
            else:
                # For 1-minute intervals, just use the next minute boundary
                next_update_time = next_minute
            
            # For DAKboard mode, add 5 seconds after the minute boundary to account for DAKboard delay
            if is_dakboard_mode:
                next_update_time = next_update_time + timedelta(seconds=5)
                self.logger.info(f"DAKboard mode: {interval_seconds}s interval aligns to {next_update_time.strftime('%H:%M:%S')} (5s after minute boundary)")
            else:
                self.logger.info(f"Using minute-aligned scheduling: {interval_seconds}s interval aligns to {next_update_time.strftime('%H:%M:%S')}")
            
        else:
            # For non-round minute intervals, use the original logic
            if interval_seconds < 60:
                # For sub-minute intervals, next update is at the next minute boundary
                next_update_time = current_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
                # For DAKboard mode, add 5 seconds after the minute boundary
                if is_dakboard_mode:
                    next_update_time = next_update_time + timedelta(seconds=5)
                    self.logger.info(f"DAKboard mode: Sub-minute interval ({interval_seconds}s), aligning to 5s after minute boundary")
                else:
                    self.logger.info(f"Sub-minute interval ({interval_seconds}s), aligning to next minute boundary")
            else:
                # For intervals >= 60 seconds that aren't round minutes, use current time + interval
                next_update_time = current_time + timedelta(seconds=interval_seconds)
                self.logger.info(f"Non-round minute interval ({interval_seconds}s), using standard scheduling")
        
        return next_update_time
    
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
                
                # Save debug screenshot if debug mode is enabled
                if self.settings.debug_mode:
                    self._save_persistent_screenshot(dashboard_image)
                
                # Update display with performance timing
                self.logger.info("Updating e-ink display...")
                
                with PrometheusTimer(self.metrics, 'display_update', refresh_type=refresh_type):
                    success = self.display.update(dashboard_image, force_full_refresh)
                
                if success:
                    self.logger.info("Display update completed successfully")
                    self.metrics.record_update_success()
                    
                    # Collect browser metrics after successful update
                    self._collect_browser_metrics()
                    
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
        self.logger.info("Starting continuous dashboard mode...")

        # Show initializing message with mode and friendly timestamp
        self._show_initializing_message()

        is_first_update = True
        intended_update_time = None
        
        try:
            while True:
                # Perform the display update
                if is_first_update:
                    self.logger.info("Performing initial display update...")
                    success = self.update_display(force_full_refresh=True)
                    is_first_update = False
                else:
                    time_str = intended_update_time.strftime("%H:%M:%S") if intended_update_time else "<none>"
                    self.logger.info(f"Update intended for: {time_str}")
                    success = self.update_display(force_full_refresh=False)
                    
                    # Record timing offset metric for non-initial updates
                    if intended_update_time:
                        actual_completion_time = datetime.now()
                        timing_offset_seconds = (actual_completion_time - intended_update_time).total_seconds()
                        self.metrics.record_update_timing_offset(timing_offset_seconds)
                
                # Calculate when the next update should occur
                current_time = datetime.now()
                next_update_time = self._calculate_next_update_time(intended_update_time or current_time)
                
                # Calculate remaining time until next update and sleep if needed
                time_until_next_update = (next_update_time - current_time).total_seconds()
                
                if time_until_next_update > 0:
                    self.logger.info(f"Update completed, waiting {time_until_next_update:.2f} seconds until next update at {next_update_time.strftime('%H:%M:%S')}...")
                    time.sleep(time_until_next_update)
                else:
                    self.logger.warning(f"Update took longer than expected, next update is {abs(time_until_next_update):.2f} seconds overdue")
                
                # Set the intended time for the next iteration
                intended_update_time = next_update_time
                
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
