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

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import Settings
from dashboard.renderer import DashboardRenderer
from display.eink_driver import EInkDriver


class PiHomeDashboard:
    """Main dashboard application class."""
    
    def __init__(self):
        """Initialize the dashboard application."""
        self.settings = Settings()
        self.renderer = DashboardRenderer(self.settings)
        self.display = EInkDriver(self.settings)
        
        # Persistent browser state
        self.persistent_browser_enabled = False
        self.browser_refresh_count = 0
        self.max_renders_before_refresh = 1440  # Refresh browser every day (1440 minutes)
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
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
    
    def update_display(self, force_full_refresh=False):
        """Update the e-ink display with current dashboard content."""
        try:
            self.logger.info("Starting display update...")
            
            # Initialize persistent browser if needed for DAKboard
            if (self.settings.dashboard_type == "dakboard" and 
                not self.persistent_browser_enabled and 
                self.settings.dakboard_url):
                
                self.logger.info("Initializing persistent browser for DAKboard...")
                success = self.renderer.start_persistent_browser(self.settings.dakboard_url)
                if success:
                    self.persistent_browser_enabled = True
                    self.browser_refresh_count = 0
                    self.logger.info("Persistent browser initialized successfully")
                else:
                    self.logger.warning("Failed to initialize persistent browser, falling back to standard rendering")
            
            # Render dashboard content
            self.logger.info("Rendering dashboard content...")
            
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
                
                # Take screenshot using persistent browser
                dashboard_image = self.renderer.render_persistent_screenshot()
                self.browser_refresh_count += 1
                
                # Fall back to standard rendering if persistent browser fails
                if dashboard_image is None:
                    self.logger.warning("Persistent browser screenshot failed, falling back to standard rendering")
                    self.persistent_browser_enabled = False
                    dashboard_image = self.renderer.render()
            else:
                # Use standard rendering for non-DAKboard or when persistent browser is not available
                dashboard_image = self.renderer.render()
            
            if dashboard_image is None:
                self.logger.error("Failed to render dashboard content")
                return False
            
            # Update display (omni-epd handles image processing)
            self.logger.info("Updating e-ink display...")
            success = self.display.update(dashboard_image, force_full_refresh)
            
            if success:
                self.logger.info("Display update completed successfully")
            else:
                self.logger.error("Display update failed")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error during display update: {e}")
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
        
        # Initial display update
        self.update_display(force_full_refresh=True)
        
        last_full_refresh = time.time()
        
        try:
            while True:
                # Wait for next update interval
                time.sleep(self.settings.update_interval)
                
                # Determine if full refresh is needed
                current_time = time.time()
                time_since_full_refresh = current_time - last_full_refresh
                force_full_refresh = time_since_full_refresh >= self.settings.full_refresh_interval
                
                # Update display
                success = self.update_display(force_full_refresh)
                
                if force_full_refresh and success:
                    last_full_refresh = current_time
                    
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
    parser.add_argument('--test-duration', type=int, default=60,
                       help='Integration test duration in seconds (default: 60)')
    parser.add_argument('--test-interval', type=int, default=3,
                       help='Integration test update interval in seconds (default: 3)')
    parser.add_argument('--collect-artifacts', action='store_true',
                       help='Collect and validate test artifacts during integration test')
    
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
                duration=args.test_duration,
                interval=args.test_interval,
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
