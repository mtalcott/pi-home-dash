"""
Dashboard renderer for Pi Home Dashboard.
Handles rendering of dashboard content using headless browser or custom layouts.
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from PIL import Image


class DashboardRenderer:
    """Main dashboard rendering class."""
    
    def __init__(self, settings):
        """Initialize the dashboard renderer."""
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.browser_bin = "chromium"
        
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

        self.logger.info(f"Rendering DAKboard from URL: {self.settings.dakboard_url}")
        return self._run_chromium(self.settings.dakboard_url, self.settings.browser_timeout)
    
    def _render_integration_test(self):
        """Render integration test dashboard using local HTML file."""
        self.logger.info("Rendering integration test dashboard")

        if not hasattr(self.settings, 'test_html_path') or self.settings.test_html_path is None:
            self.logger.error("Integration test HTML path not configured")
            return None

        if not self.settings.test_html_path.exists():
            self.logger.error(f"Integration test HTML file not found: {self.settings.test_html_path}")
            return None

        file_url = f"file://{self.settings.test_html_path.absolute()}"
        self.logger.info(f"Rendering integration test from: {file_url}")

        # Use a shorter timeout for tests
        timeout = min(self.settings.browser_timeout, 15)
        return self._run_chromium(file_url, timeout)
    
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

    def _run_chromium(self, url, timeout):
        """Render a URL using headless Chromium and return a PIL Image."""
        try:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_path = temp_file.name

            cmd = [
                self.browser_bin,
                '--headless=new',
                '--disable-gpu',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-extensions',
                '--disable-plugins',
                '--virtual-time-budget=10000',
                f'--window-size={self.settings.browser_width},{self.settings.browser_height}',
                f'--screenshot={temp_path}',
                url
            ]

            self.logger.debug(f"Running command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode != 0:
                self.logger.error(f"Chromium failed: {result.stderr}")
                return None

            if Path(temp_path).exists():
                image = Image.open(temp_path)
                Path(temp_path).unlink()
                self.logger.info(f"Successfully rendered {url}")
                return image
            else:
                self.logger.error("Screenshot file not created")
                return None

        except subprocess.TimeoutExpired:
            self.logger.error(f"Browser rendering timed out for {url}")
            return None
        except Exception as e:
            self.logger.error(f"Error rendering URL {url}: {e}")
            return None
