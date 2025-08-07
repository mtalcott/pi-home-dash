"""
Dashboard renderer for Pi Home Dashboard.
Handles rendering of dashboard content using headless browser or custom layouts.
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from PIL import Image
import io


class DashboardRenderer:
    """Main dashboard rendering class."""
    
    def __init__(self, settings):
        """Initialize the dashboard renderer."""
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
    def render(self):
        """Render the dashboard and return a PIL Image."""
        try:
            if self.settings.dashboard_type == "dakboard":
                return self._render_dakboard()
            elif self.settings.dashboard_type == "custom":
                return self._render_custom()
            elif self.settings.dashboard_type == "integration_test":
                return self._render_integration_test()
            else:
                raise ValueError(f"Unknown dashboard type: {self.settings.dashboard_type}")
                
        except Exception as e:
            self.logger.error(f"Error rendering dashboard: {e}")
            return None
    
    def _render_dakboard(self):
        """Render DAKboard using headless browser."""
        if not self.settings.dakboard_url:
            self.logger.error("DAKboard URL not configured")
            return None
            
        try:
            self.logger.info(f"Rendering DAKboard from URL: {self.settings.dakboard_url}")
            
            # Create temporary file for screenshot
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Use chromium to take screenshot
            cmd = [
                'chromium-browser',
                '--headless',
                '--disable-gpu',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',  # Disable image loading for faster rendering
                '--virtual-time-budget=10000',  # 10 second budget
                f'--window-size={self.settings.browser_width},{self.settings.browser_height}',
                f'--screenshot={temp_path}',
                self.settings.dakboard_url
            ]
            
            self.logger.debug(f"Running command: {' '.join(cmd)}")
            
            # Run chromium command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.settings.browser_timeout
            )
            
            if result.returncode != 0:
                self.logger.error(f"Chromium failed: {result.stderr}")
                return None
            
            # Load the screenshot
            if Path(temp_path).exists():
                image = Image.open(temp_path)
                # Clean up temp file
                Path(temp_path).unlink()
                
                self.logger.info("DAKboard rendered successfully")
                return image
            else:
                self.logger.error("Screenshot file not created")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.error("Browser rendering timed out")
            return None
        except Exception as e:
            self.logger.error(f"Error rendering DAKboard: {e}")
            return None
    
    def _render_integration_test(self):
        """Render integration test dashboard using local HTML file."""
        try:
            self.logger.info("Rendering integration test dashboard")
            
            # Check if test HTML file is configured and exists
            if not hasattr(self.settings, 'test_html_path') or self.settings.test_html_path is None:
                self.logger.error("Integration test HTML path not configured")
                return None
                
            if not self.settings.test_html_path.exists():
                self.logger.error(f"Integration test HTML file not found: {self.settings.test_html_path}")
                return None
            
            # Convert file path to file:// URL for browser
            file_url = f"file://{self.settings.test_html_path.absolute()}"
            self.logger.info(f"Rendering integration test from: {file_url}")
            
            # Create temporary file for screenshot
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Use chromium to take screenshot (reuse existing browser setup)
            cmd = [
                'chromium',
                '--headless',
                '--disable-gpu',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-extensions',
                '--disable-plugins',
                '--virtual-time-budget=5000',  # 5 second budget for faster test cycles
                f'--window-size={self.settings.browser_width},{self.settings.browser_height}',
                f'--screenshot={temp_path}',
                file_url
            ]
            
            self.logger.debug(f"Running command: {' '.join(cmd)}")
            
            # Run chromium command with shorter timeout for tests
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=min(self.settings.browser_timeout, 15)  # Max 15 seconds for tests
            )
            
            if result.returncode != 0:
                self.logger.error(f"Chromium failed: {result.stderr}")
                return None
            
            # Load the screenshot
            if Path(temp_path).exists():
                image = Image.open(temp_path)
                # Clean up temp file
                Path(temp_path).unlink()
                
                self.logger.info("Integration test dashboard rendered successfully")
                return image
            else:
                self.logger.error("Screenshot file not created")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.error("Integration test rendering timed out")
            return None
        except Exception as e:
            self.logger.error(f"Error rendering integration test dashboard: {e}")
            return None
    
    def _render_custom(self):
        """Render custom dashboard layout."""
        try:
            self.logger.info("Rendering custom dashboard")
            
            # Create a blank image with display dimensions
            image = Image.new('RGB', 
                            (self.settings.display_width, self.settings.display_height))
            # Fill with white background
            image.paste((255, 255, 255), (0, 0, self.settings.display_width, self.settings.display_height))
            
            # TODO: Implement custom dashboard rendering
            # This would involve:
            # 1. Fetching calendar data
            # 2. Fetching weather data
            # 3. Fetching to-do data
            # 4. Creating a custom layout
            # 5. Drawing text and graphics on the image
            
            self.logger.warning("Custom dashboard rendering not yet implemented")
            return image
            
        except Exception as e:
            self.logger.error(f"Error rendering custom dashboard: {e}")
            return None
    
    def _render_with_xvfb(self, url):
        """Alternative rendering method using Xvfb virtual display."""
        try:
            self.logger.info("Using Xvfb for rendering")
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Use xvfb-run with chromium
            cmd = [
                'xvfb-run', '-a', '-s', '-screen 0 1920x1080x24',
                'chromium-browser',
                '--headless',
                '--disable-gpu',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                f'--window-size={self.settings.browser_width},{self.settings.browser_height}',
                f'--screenshot={temp_path}',
                url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.settings.browser_timeout
            )
            
            if result.returncode == 0 and Path(temp_path).exists():
                image = Image.open(temp_path)
                Path(temp_path).unlink()
                return image
            else:
                self.logger.error(f"Xvfb rendering failed: {result.stderr}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error with Xvfb rendering: {e}")
            return None
    
    def test_browser_availability(self):
        """Test if required browser tools are available."""
        try:
            # Test chromium
            result = subprocess.run(['chromium-browser', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.info(f"Chromium available: {result.stdout.strip()}")
                return True
            else:
                self.logger.error("Chromium not available")
                return False
                
        except FileNotFoundError:
            self.logger.error("Chromium browser not found")
            return False
        except Exception as e:
            self.logger.error(f"Error testing browser: {e}")
            return False
