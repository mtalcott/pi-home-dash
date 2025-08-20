"""
Configuration settings for Pi Home Dashboard.

Minimal env-based migration:
- Only wire up env vars that are already used by the code paths:
  DAKBOARD_URL, DEBUG, UPDATE_INTERVAL, FULL_REFRESH_INTERVAL,
  DISPLAY_WIDTH, DISPLAY_HEIGHT, DASHBOARD_TYPE
- Keep other settings as internal defaults (no new envs introduced).
- Implement load_from_file/save_to_file for simple .env-style files
  without requiring python-dotenv (docker-compose will load .env).
"""

import os
from pathlib import Path
from typing import Optional


def _get_env_str(name: str, default: str) -> str:
    val = os.getenv(name)
    return default if val is None else val


def _get_env_int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    try:
        return int(val)
    except Exception:
        return default


def _get_env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    """Main configuration class for the dashboard."""

    # Centralized defaults (used-only envs will override these)
    DEFAULTS = {
        # Display settings
        "display_width": 400,
        "display_height": 200,
        "display_rotation": 0,  # 0, 90, 180, 270 degrees

        # Update intervals (in seconds)
        "update_interval": 60,           # 1 minute
        "full_refresh_interval": 3600,   # 1 hour

        # Dashboard settings
        "dashboard_type": "dakboard",    # "dakboard" or "custom" or "integration_test"
        "dakboard_url": "",

        # System settings
        "debug_mode": False,
        "log_level": "INFO",
        "log_file": "/var/log/pi-dashboard.log",

        # Browser settings for rendering
        "browser_timeout": 30,  # seconds

        # E-ink display specific settings
        "eink_partial_refresh_limit": 10,  # Number of partial refreshes before full refresh
        "eink_ghosting_prevention": True,

        # Omni-EPD settings
        "epd_device": "waveshare_epd.it8951",  # Device type for 10.3" display
        "epd_mode": "bw",  # Display mode: "bw" or "gray16"
    }

    def __init__(self):
        """Initialize settings with defaults, then apply env overrides where used."""
        # Paths
        self.project_root = Path(__file__).resolve().parents[2]
        self.cache_dir = self.project_root / "cache"
        self.temp_dir = self.project_root / "temp"

        # Initialize with defaults
        self.display_width = self.DEFAULTS["display_width"]
        self.display_height = self.DEFAULTS["display_height"]
        self.display_rotation = self.DEFAULTS["display_rotation"]

        self.update_interval = self.DEFAULTS["update_interval"]
        self.full_refresh_interval = self.DEFAULTS["full_refresh_interval"]

        self.dashboard_type = self.DEFAULTS["dashboard_type"]
        self.dakboard_url = self.DEFAULTS["dakboard_url"]

        self.debug_mode = self.DEFAULTS["debug_mode"]
        self.log_level = self.DEFAULTS["log_level"]
        self.log_file = self.DEFAULTS["log_file"]

        self.browser_width = self.display_width
        self.browser_height = self.display_height
        self.browser_timeout = self.DEFAULTS["browser_timeout"]

        self.eink_partial_refresh_limit = self.DEFAULTS["eink_partial_refresh_limit"]
        self.eink_ghosting_prevention = self.DEFAULTS["eink_ghosting_prevention"]

        self.epd_device = self.DEFAULTS["epd_device"]
        self.epd_mode = self.DEFAULTS["epd_mode"]

        # Integration test settings
        self.test_html_path: Optional[Path] = None  # Path to test HTML file for integration tests

        # Apply env overrides for settings that are actually used by the code
        self._apply_env_overrides()

        # Create directories if they don't exist
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        self.temp_dir.mkdir(exist_ok=True, parents=True)

        # Keep browser size in sync with display by default
        self.browser_width = self.display_width
        self.browser_height = self.display_height

    def _apply_env_overrides(self):
        """Apply environment variable overrides for used-only settings."""
        # Dashboard routing
        self.dashboard_type = _get_env_str("DASHBOARD_TYPE", self.dashboard_type)
        # Dakboard URL (already env-aware originally)
        self.dakboard_url = _get_env_str("DAKBOARD_URL", self.dakboard_url)

        # Logging/debug
        self.debug_mode = _get_env_bool("DEBUG", self.debug_mode)

        # Update cadence
        self.update_interval = _get_env_int("UPDATE_INTERVAL", self.update_interval)
        self.full_refresh_interval = _get_env_int("FULL_REFRESH_INTERVAL", self.full_refresh_interval)
        self.browser_timeout = _get_env_int("BROWSER_TIMEOUT", self.browser_timeout)

        # Display geometry
        self.display_width = _get_env_int("DISPLAY_WIDTH", self.display_width)
        self.display_height = _get_env_int("DISPLAY_HEIGHT", self.display_height)

    def validate(self):
        """Validate configuration settings."""
        errors = []

        if self.dashboard_type == "dakboard" and not self.dakboard_url:
            errors.append("DAKboard URL is required when using DAKboard dashboard type")

        if self.display_width <= 0 or self.display_height <= 0:
            errors.append("Display dimensions must be positive integers")

        if self.display_rotation not in (0, 90, 180, 270):
            errors.append("Display rotation must be one of: 0, 90, 180, 270")

        if self.browser_timeout <= 0:
            errors.append("Browser timeout must be positive")

        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(errors))

        return True

    def load_from_file(self, config_file: Path):
        """Load settings from a simple .env-style file and apply to environment.

        Notes:
        - This does not require python-dotenv.
        - Lines starting with '#' are comments.
        - Only keys without quotes and simple 'KEY=VALUE' are supported.
        - After loading, environment variables for used-only settings are applied.
        """
        cfg_path = Path(config_file)
        if not cfg_path.exists():
            raise FileNotFoundError(f"Config file not found: {cfg_path}")

        with cfg_path.open("r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                # Remove optional surrounding quotes
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                os.environ[key] = value

        # Re-apply env overrides
        self._apply_env_overrides()

    def save_to_file(self, config_file: Path):
        """Save current used-only settings to a .env-style configuration file."""
        cfg_path = Path(config_file)
        lines = [
            "# Pi Home Dashboard Environment Configuration",
            "# Generated by Settings.save_to_file",
            "",
            "# Dashboard Configuration",
            f"DAKBOARD_URL={self.dakboard_url}",
            f"DEBUG={'true' if self.debug_mode else 'false'}",
            f"DASHBOARD_TYPE={self.dashboard_type}",
            "",
            "# Update Cadence",
            f"UPDATE_INTERVAL={self.update_interval}",
            f"FULL_REFRESH_INTERVAL={self.full_refresh_interval}",
            "",
            "# Display Geometry",
            f"DISPLAY_WIDTH={self.display_width}",
            f"DISPLAY_HEIGHT={self.display_height}",
            "",
            "# Other environment variables like DISPLAY are typically set by the runtime (e.g., docker-compose).",
        ]
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
