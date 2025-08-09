"""
Configuration settings for Pi Home Dashboard.
"""

import os
from pathlib import Path
from typing import Optional


class Settings:
    """Main configuration class for the dashboard."""
    
    def __init__(self):
        """Initialize settings with default values."""
        
        # Display settings
        self.display_width = 1872
        self.display_height = 1404
        self.display_rotation = 0  # 0, 90, 180, 270 degrees
        
        # Update intervals (in seconds)
        self.update_interval = 60  # 1 minute
        self.full_refresh_interval = 3600  # 1 hour
        
        # Dashboard settings
        self.dashboard_type = "dakboard"  # "dakboard" or "custom"
        self.dakboard_url = os.getenv("DAKBOARD_URL", "")
        
        # System settings
        self.debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = "INFO"
        self.log_file = "/var/log/pi-dashboard.log"
        
        # Paths
        self.project_root = Path(__file__).parent.parent.parent
        self.cache_dir = self.project_root / "cache"
        self.temp_dir = self.project_root / "temp"
        
        # Create directories if they don't exist
        self.cache_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        
        # Browser settings for rendering
        self.browser_width = self.display_width
        self.browser_height = self.display_height
        self.browser_timeout = 30  # seconds
        
        # E-ink display specific settings
        self.eink_partial_refresh_limit = 10  # Number of partial refreshes before full refresh
        self.eink_ghosting_prevention = True
        
        # Omni-EPD settings
        self.epd_device = "waveshare_epd.it8951"  # Device type for 10.3" display
        self.epd_mode = "bw"  # Display mode: "bw" or "gray16"
        
        # Integration test settings
        self.test_html_path: Optional[Path] = None  # Path to test HTML file for integration tests
        
    def validate(self):
        """Validate configuration settings."""
        errors = []
        
        if self.dashboard_type == "dakboard" and not self.dakboard_url:
            errors.append("DAKboard URL is required when using DAKboard dashboard type")
            
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(errors))
            
        return True
    
    def load_from_file(self, config_file):
        """Load settings from a configuration file."""
        # TODO: Implement configuration file loading
        pass
    
    def save_to_file(self, config_file):
        """Save current settings to a configuration file."""
        # TODO: Implement configuration file saving
        pass
