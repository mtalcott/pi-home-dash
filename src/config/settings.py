"""
Configuration settings for Pi Home Dashboard.

Minimal env-based migration:
- Only wire up env vars that are already used by the code paths:
  DAKBOARD_URL, DEBUG, UPDATE_INTERVAL, EINK_PARTIAL_REFRESH_LIMIT,
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


def _get_env_float(name: str, default: float) -> float:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    try:
        return float(val)
    except Exception:
        return default


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
        "eink_partial_refresh_limit": 60,  # Number of partial refreshes before full refresh
        "eink_ghosting_prevention": True,

        # Display driver settings
        "display_type": "it8951",  # "it8951" for hardware, "mock" for testing
        "epd_mode": "bw",  # Display mode: "bw" or "gray16"
        
        # IT8951 specific settings
        "it8951_vcom": -1.46,      # VCOM voltage for IT8951 display (-1.5V to -3.0V range)
        "it8951_spi_hz": 16000000, # SPI frequency in Hz (16MHz for balanced performance/stability)
        "it8951_mirror": True,     # Mirror display output to fix reversed images
        "it8951_rotate": None,     # Rotation: None, 90, 180, 270

        # Prometheus metrics settings
        "prometheus_port": 8000,
        "prometheus_enabled": True,
    }

    def __init__(self):
        """Initialize settings with defaults, then apply env overrides where used."""
        # Paths
        self.project_root = Path(__file__).resolve().parents[2]
        self.temp_dir = self.project_root / "temp"

        # Initialize with defaults
        self.display_width = self.DEFAULTS["display_width"]
        self.display_height = self.DEFAULTS["display_height"]
        self.display_rotation = self.DEFAULTS["display_rotation"]

        self.update_interval = self.DEFAULTS["update_interval"]

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

        self.display_type = self.DEFAULTS["display_type"]
        self.epd_mode = self.DEFAULTS["epd_mode"]

        # IT8951 specific settings
        self.it8951_vcom = self.DEFAULTS["it8951_vcom"]
        self.it8951_spi_hz = self.DEFAULTS["it8951_spi_hz"]
        self.it8951_mirror = self.DEFAULTS["it8951_mirror"]
        self.it8951_rotate = self.DEFAULTS["it8951_rotate"]

        # Prometheus metrics settings
        self.prometheus_port = self.DEFAULTS["prometheus_port"]
        self.prometheus_enabled = self.DEFAULTS["prometheus_enabled"]

        # Integration test settings
        self.test_html_path: Optional[Path] = None  # Path to test HTML file for integration tests

        # Apply env overrides for settings that are actually used by the code
        self._apply_env_overrides()

        # Create directories if they don't exist with proper permissions
        self._ensure_directory_writable(self.temp_dir)

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
        self.browser_timeout = _get_env_int("BROWSER_TIMEOUT", self.browser_timeout)
        
        # E-ink display settings
        self.eink_partial_refresh_limit = _get_env_int("EINK_PARTIAL_REFRESH_LIMIT", self.eink_partial_refresh_limit)

        # Display geometry
        self.display_width = _get_env_int("DISPLAY_WIDTH", self.display_width)
        self.display_height = _get_env_int("DISPLAY_HEIGHT", self.display_height)

        # Display driver type
        self.display_type = _get_env_str("DISPLAY_TYPE", self.display_type)

        # IT8951 specific settings
        self.it8951_vcom = _get_env_float("IT8951_VCOM", self.it8951_vcom)
        self.it8951_spi_hz = _get_env_int("IT8951_SPI_HZ", self.it8951_spi_hz)
        self.it8951_mirror = _get_env_bool("IT8951_MIRROR", self.it8951_mirror)
        
        # Handle IT8951_ROTATE which can be None or int
        rotate_env = os.getenv("IT8951_ROTATE")
        if rotate_env is not None and rotate_env.strip().lower() not in ("none", "null", ""):
            try:
                self.it8951_rotate = int(rotate_env)
            except ValueError:
                pass  # Keep default value

    def _ensure_directory_writable(self, directory: Path):
        """Ensure directory exists and is writable by current user."""
        try:
            # Create directory if it doesn't exist
            directory.mkdir(exist_ok=True, parents=True)
            
            # Test if we can write to the directory
            test_file = directory / ".write_test"
            try:
                test_file.touch()
                test_file.unlink()
            except (PermissionError, OSError):
                # If we can't write, try to fix permissions if possible
                import stat
                try:
                    # Make directory writable by owner
                    directory.chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                except (PermissionError, OSError):
                    # If we can't fix permissions, log a warning but continue
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Directory {directory} may not be writable - some features may not work")
                    
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not ensure directory {directory} is writable: {e}")

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
            "",
            "# Display Geometry",
            f"DISPLAY_WIDTH={self.display_width}",
            f"DISPLAY_HEIGHT={self.display_height}",
            "",
            "# Other environment variables like DISPLAY are typically set by the runtime (e.g., docker-compose).",
        ]
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
