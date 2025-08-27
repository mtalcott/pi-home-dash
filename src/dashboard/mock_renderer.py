"""
Mock dashboard renderer for testing purposes.
Uses the existing test_dashboard.html file when dashboard_type='mock'.
"""

import logging
from pathlib import Path
from typing import Optional
from PIL import Image

from .renderer import DashboardRenderer


class MockDashboardRenderer(DashboardRenderer):
    """Mock renderer that uses test_dashboard.html instead of DAKboard."""
    
    def __init__(self, settings):
        """Initialize the mock dashboard renderer."""
        super().__init__(settings)
        self.logger = logging.getLogger(__name__)
        
        # Mock mode detection
        self.mock_mode = settings.dashboard_type == 'mock'
        
        if self.mock_mode:
            # Override the dashboard URL to use local test file
            self.test_html_path = Path(__file__).parent.parent / "test" / "test_dashboard.html"
            if self.test_html_path.exists():
                self.dashboard_url = f"file://{self.test_html_path.absolute()}"
                self.logger.info(f"Mock mode enabled - using test dashboard: {self.dashboard_url}")
            else:
                self.logger.error(f"Test dashboard file not found: {self.test_html_path}")
                self.mock_mode = False
        else:
            self.logger.debug("Mock dashboard renderer available but not active")
    
    def render(self) -> Optional[Image.Image]:
        """
        Render dashboard image using test HTML file in mock mode.
        
        Returns:
            PIL Image or None if rendering fails
        """
        if not self.mock_mode:
            # Fall back to parent class (normal DAKboard rendering)
            return super().render()
        
        try:
            self.logger.info("Rendering mock dashboard from test HTML")
            
            # Temporarily change dashboard type to integration_test and set test HTML path
            original_dashboard_type = self.settings.dashboard_type
            original_test_html_path = getattr(self.settings, 'test_html_path', None)
            
            self.settings.dashboard_type = 'integration_test'
            self.settings.test_html_path = self.test_html_path
            
            # Render using the parent class integration_test method
            result = super().render()
            
            # Restore original settings
            self.settings.dashboard_type = original_dashboard_type
            if original_test_html_path is not None:
                self.settings.test_html_path = original_test_html_path
            elif hasattr(self.settings, 'test_html_path'):
                delattr(self.settings, 'test_html_path')
            
            if result:
                self.logger.info("Mock dashboard rendered successfully")
            else:
                self.logger.error("Mock dashboard rendering failed")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error rendering mock dashboard: {e}")
            return None
    
    def is_mock_mode(self) -> bool:
        """Check if mock mode is active."""
        return self.mock_mode
    
    def get_mock_stats(self) -> dict:
        """Get mock renderer statistics."""
        return {
            'mock_mode': self.mock_mode,
            'test_html_path': str(self.test_html_path) if hasattr(self, 'test_html_path') else None,
            'dashboard_url': getattr(self, 'dashboard_url', None)
        }
