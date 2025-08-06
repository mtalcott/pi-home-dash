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
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
    def _setup_logging(self):
        """Configure logging based on settings."""
        level = logging.DEBUG if self.settings.debug_mode else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/var/log/pi-dashboard.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def update_display(self, force_full_refresh=False):
        """Update the e-ink display with current dashboard content."""
        try:
            self.logger.info("Starting display update...")
            
            # Render dashboard content
            self.logger.info("Rendering dashboard content...")
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
    
    args = parser.parse_args()
    
    # Create dashboard instance
    dashboard = PiHomeDashboard()
    
    # Override debug setting if specified
    if args.debug:
        dashboard.settings.debug_mode = True
        dashboard._setup_logging()
    
    try:
        if args.test:
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
