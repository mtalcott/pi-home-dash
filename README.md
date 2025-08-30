# Pi Home Dashboard - E-Ink Smart Calendar

A DIY e-ink display for home with smart calendar functionality, similar to Skylight Smart Calendar or DAKboard, powered by a Raspberry Pi Zero 2 W.

## Project Overview

This project creates a home smart calendar using:
- **Display**: Waveshare 10.3" e-Paper HAT (1872×1404, B&W)
- **Computer**: Raspberry Pi Zero 2 W
- **Features**: Calendar, weather, and to-do lists
- **Frame**: White shadow box frame for clean presentation
- **Testing**: Docker virtualization using lukechilds/dockerpi
- **Display Library**: GregDMeyer/IT8951 for enhanced partial refresh support

## Hardware Components

### Required Components
- Waveshare 10.3" e-Paper HAT (IT8951 controller) - ~$200-203
- Raspberry Pi Zero 2 W (with pre-soldered GPIO header) - ~$22
- 5V/3A Micro USB Power Supply - ~$6.49
- 16GB Class 10 MicroSD Card - ~$4.49
- Mini HDMI to HDMI Adapter (for setup)
- Micro USB OTG Adapter (for keyboard/mouse during setup)

### Display Specifications
- **Model**: Waveshare 10.3" e-Paper HAT
- **Controller**: IT8951
- **Outer dimensions**: 216.70 × 174.40mm
- **Active display area**: 209.66 × 157.25mm
- **Resolution**: 1872×1404 pixels
- **Refresh time**: <1 second full refresh, partial refresh support
- **Interface**: SPI/GPIO connection to Raspberry Pi
- **IT8951 controller**: Direct communication via GregDMeyer/IT8951 library

### Frame Options
- 8×10" White Shadow Box Frame
- Interior depth: 1.5" (38mm) - sufficient for Pi and components
- Can stand in landscape orientation
- Fully enclosed back panel

## Software Architecture

### Core Components
1. **Dashboard Renderer**: Headless browser to render DAKboard or custom dashboard
2. **Display Driver**: Uses IT8951 library for direct e-ink display control with enhanced partial refresh
3. **Scheduler**: Automated updates every few minutes
4. **Configuration**: Centralized settings management

### Display Library - IT8951
This project uses the [GregDMeyer/IT8951](https://github.com/GregDMeyer/IT8951) library for enhanced e-ink display control:
- **Direct Controller Access**: Direct communication with IT8951 controller for optimal performance
- **Enhanced Partial Refresh**: Region-specific partial updates with configurable refresh modes
- **Advanced Display Modes**: GC16 for full refresh, DU for fast partial refresh
- **Mock Testing Support**: Simulation mode for development and CI/CD

### Data Sources
- DAKboard dashboard content (handles calendar, weather, todos, and custom widgets)

### Performance Optimization - Persistent Browser

The dashboard includes a persistent browser optimization that dramatically improves rendering speed:

- **Original Method**: Spawned new Chromium process for each render (~3 minutes on Pi Zero 2 W)
- **Optimized Method**: Keeps Chromium instance running and takes screenshots (~2-5 seconds)

**Key Features:**
- Automatic initialization for DAKboard rendering
- Memory-optimized Chrome flags for Pi Zero 2 W
- Daily browser refresh to prevent stale content
- Fallback to standard rendering if persistent browser fails
- E-ink display optimizations (disabled animations, videos)

**Performance Comparison:**
| Method | Initial Load | Subsequent Renders | Memory Usage |
|--------|-------------|-------------------|--------------|
| Original (subprocess) | ~3 minutes | ~3 minutes | Low (temporary) |
| Persistent Browser | ~30-60 seconds | ~2-5 seconds | Higher (persistent) |

The persistent browser is automatically enabled for DAKboard rendering and uses Playwright.

## GPIO SPI Connection

### Pi Zero 2 W to Waveshare 10.3" HAT
The IT8951 library handles the low-level SPI communication, but the physical connections are:

| IT8951 Pin | Raspberry Pi GPIO | Function |
|------------|-------------------|----------|
| VCC        | Pin 2 or 4        | 5V Power |
| GND        | Pin 6             | Ground   |
| DIN (MOSI) | Pin 19            | SPI MOSI |
| DOUT (MISO)| Pin 21            | SPI MISO |
| CLK (SCK)  | Pin 23            | SPI Clock|
| CS         | Pin 24            | Chip Select |
| HRDY (BUSY)| Pin 18            | GPIO Input |
| RST        | Pin 22            | GPIO Output |

## Development Setup

### Local Development
```bash
# Clone the repository
git clone <repository-url>
cd pi-home-dash

# Install dependencies locally
pip install -r requirements.txt

# Build the Docker image
docker-compose build

# Test the display (simulation mode if no hardware)
docker-compose run --rm pi-home-dash python src/main.py --test

# Run single update
docker-compose run --rm pi-home-dash python src/main.py --update
```

### Docker Compose Testing
```bash
# Build the image
docker-compose build

# Run a single test
docker-compose run --rm pi-home-dash python src/main.py --test

# Run with debug logging
docker-compose run --rm pi-home-dash python src/main.py --debug --test

# Run in continuous mode (production-like)
docker-compose run --rm pi-home-dash python src/main.py --continuous
```

## Project Structure

```
pi-home-dash/
├── src/
│   ├── main.py              # Main application entry point
│   ├── dashboard/
│   │   └── renderer.py      # Dashboard rendering logic
│   ├── display/
│   │   ├── it8951_driver.py # IT8951 driver for enhanced e-ink display control
│   │   └── image_processor.py # Additional image utilities (optional)
│   ├── config/
│   │   └── settings.py      # Configuration management
│   └── test/
│       ├── __init__.py      # Test package initialization
│       ├── integration_test.py # End-to-end integration tests
│       └── test_dashboard.html # HTML test file for dashboard rendering
├── test_setup.py           # Test setup and configuration
├── test_results/           # Test output directory (screenshots, reports, logs)
├── logs/                   # Application logs directory
├── temp/                   # Temporary files directory
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose for testing
├── .env.example           # Environment variables template
└── README.md              # This file
```

## Installation Guide

### Quick Setup (Recommended)
For automated installation on a Raspberry Pi:

```bash
# One-command install
curl -sSL https://raw.githubusercontent.com/mtalcott/pi-home-dash/master/install.sh | bash
```

This automatically:
- Installs all system dependencies (including SPI setup)
- Creates Python virtual environment
- Installs Python packages from requirements.txt
- Creates systemd service for auto-startup
- Tests the installation

### Manual Setup
If you prefer manual installation:

```bash
# Clone repository
git clone <repository-url> ~/pi-home-dash
cd ~/pi-home-dash

# Run setup script
chmod +x setup_pi.sh
./setup_pi.sh
```

### Hardware Assembly
1. Connect the Waveshare 10.3" e-Paper HAT to Raspberry Pi Zero 2 W via GPIO
2. Install Pi and display in shadow box frame
3. Connect power supply and boot

### Post-Setup Configuration
1. Edit `~/pi-home-dash/.env` to configure your DAKboard URL
2. Reboot Pi to enable SPI: `sudo reboot`
3. Start service: `sudo systemctl start pi-home-dash`
4. Check status: `sudo systemctl status pi-home-dash`

### Setup Scripts
The setup process uses shared components between Docker and Pi environments:
- **`setup_pi.sh`**: Main Pi setup script
- **`scripts/common_setup.sh`**: Shared setup functions
- **`install.sh`**: Quick install wrapper
- Same dependencies and directory structure as Dockerfile

## Usage

### Command Line Options
```bash
# Test display with built-in test pattern
docker-compose run --rm pi-home-dash python src/main.py --test

# Force single display update
docker-compose run --rm pi-home-dash python src/main.py --update

# Run in continuous mode (default)
docker-compose run --rm pi-home-dash python src/main.py --continuous

# Debug mode with verbose logging
docker-compose run --rm pi-home-dash python src/main.py --debug

# Run integration test (end-to-end pipeline test)
docker-compose run --rm pi-home-dash python src/main.py --integration-test --duration 60 --interval 3
```

### Integration Testing

The project includes comprehensive end-to-end integration tests that validate the complete pipeline from HTML rendering to virtual e-ink display updates:

```bash
# Run integration test with default settings (60s duration, 3s intervals)
docker-compose run --rm pi-home-dash python src/main.py --integration-test

# Custom test duration and intervals
docker-compose run --rm pi-home-dash python src/main.py --integration-test --duration 30 --interval 2

# With artifact collection and validation
docker-compose run --rm pi-home-dash python src/main.py --integration-test --collect-artifacts

# Run test module directly
docker-compose run --rm pi-home-dash python src/test/integration_test.py --duration 15 --interval 3
```

**Integration Test Features:**
- Tests complete HTML → Image → Display pipeline
- Uses dynamic HTML content with real-time clock
- Validates performance metrics (<2s per update cycle)
- Generates screenshots, reports, and performance data
- Success criteria validation (>95% success rate)
- Runs entirely in Docker with virtual e-ink display

**Test Artifacts:**
- Screenshots: `test_results/screenshots/`
- Performance reports: `test_results/reports/`
- Detailed logs: `test_results/logs/`

### Automatic Operation
Once installed, the dashboard will:
1. Boot automatically with the Pi
2. Load and render the dashboard content
3. Update the e-ink display every 5 minutes
4. Handle partial refreshes for time updates
5. Perform full refresh periodically to clear ghosting

### Display Configuration
The display can be configured via environment variables in `.env`:
```bash
# IT8951 display settings
DISPLAY_TYPE=it8951    # Use IT8951 driver for hardware, 'mock' for testing
```

Display behavior is controlled through `src/config/settings.py` which reads these environment variables and configures the IT8951Driver accordingly.

## Testing with Docker Compose

This project includes Docker Compose support for testing without physical hardware using a single consolidated service with different run commands:

### Usage Examples

```bash
# Build the image
docker-compose build

# Run single test (default command)
docker-compose run --rm pi-home-dash python src/main.py --test

# Run with debug logging
docker-compose run --rm pi-home-dash python src/main.py --debug --test

# Run integration test (results saved to ./test_results/ on host)
docker-compose run --rm pi-home-dash python src/main.py --integration-test

# Run single update
docker-compose run --rm pi-home-dash python src/main.py --update

# Run in continuous mode (production-like)
docker-compose run --rm pi-home-dash python src/main.py --continuous

# Development mode with live code reloading (mount source code)
docker-compose run --rm -v ./src:/app/src --tty --interactive pi-home-dash python src/main.py --debug --test

# Run in continuous mode (production-like) with custom environment variables
DEBUG=false DAKBOARD_URL=https://dakboard.com/display/uuid/DAKBOARD_UUID docker-compose run --rm pi-home-dash python src/main.py --continuous

# Run background service with restart policy
docker-compose up -d --restart unless-stopped pi-home-dash

# View logs
docker-compose logs -f pi-home-dash

# Stop services
docker-compose down
```

### Configuration

- **Volumes**: Persistent cache, temp, and log directories
- **Environment Variables**: Configurable via `.env` file or command line
- **Shared Build**: Single Docker image used for all operations
- **Flexible Commands**: Different functionality via command arguments

### Environment Configuration

Create a `.env` file from the example to customize your setup:

```bash
# Copy the example environment file
cp .env.example .env

# Edit the configuration
nano .env
```

Key environment variables:
- `DAKBOARD_URL`: Your DAKboard screen URL
- `DEBUG`: Enable debug logging (true/false)
- `UPDATE_INTERVAL`: Update frequency in seconds (default: 300)
- `DISPLAY`: X11 display for headless browser (default: :99)

### Quick Start Commands

```bash
# Setup environment
cp .env.example .env

# Build and test
docker-compose build
docker-compose run --rm pi-home-dash

# Development with live reloading
docker-compose up pi-home-dash

# Production mode
docker-compose up -d pi-home-dash

# View logs
docker-compose logs -f pi-home-dash

# Stop services
docker-compose down
```

## IT8951 Integration

### Benefits
- **Direct Controller Access**: Direct communication with IT8951 controller for optimal performance
- **Enhanced Partial Refresh**: Region-specific partial updates with configurable refresh modes
- **Advanced Display Modes**: GC16 for full refresh, DU for fast partial refresh
- **Mock Testing Support**: Simulation mode for development and CI/CD
- **Performance Optimization**: Faster refresh times and better control over display behavior

### Configuration Options
The IT8951 driver is configured via environment variables and settings:

Environment variables in `.env`:
```bash
# Display configuration
DISPLAY_TYPE=it8951    # Use IT8951 driver for hardware, 'mock' for testing
```

The driver automatically handles:
- SPI communication setup
- Display initialization
- Partial refresh region management
- Mock mode for testing without hardware
- Performance monitoring and refresh counting

## Troubleshooting

### Common Issues
- **Display not updating**: Check SPI connection and enable SPI in raspi-config
- **Slow rendering**: Ensure sufficient power supply (5V/2.5A minimum)
- **Ghosting on display**: Perform full refresh periodically (handled automatically by IT8951Driver)
- **Network issues**: Check Wi-Fi configuration and DAKboard URL accessibility
- **Mock mode issues**: Verify DISPLAY_TYPE environment variable is set correctly

### Debug Commands
```bash
# Check SPI interface
ls /dev/spi*

# Test GPIO connections (if needed)
gpio readall

# Monitor system logs
journalctl -u pi-dashboard -f

# Run with debug logging
docker-compose run --rm pi-home-dash python src/main.py --debug

# Test IT8951 driver directly
python -c "from src.display.it8951_driver import IT8951Driver; from src.config.settings import Settings; driver = IT8951Driver(Settings()); print('Driver initialized successfully')"
```

### Display Testing
```bash
# Test with project (includes IT8951 driver test)
docker-compose run --rm pi-home-dash python src/main.py --test

# Test in mock mode
DISPLAY_TYPE=mock docker-compose run --rm pi-home-dash python src/main.py --test

# Test partial refresh functionality
docker-compose run --rm pi-home-dash python src/main.py --integration-test --duration 30
```

### Persistent Browser Testing
```bash
# Test persistent browser functionality
python test_persistent_browser.py

# Test individual components in Python
python -c "
from src.config.settings import Settings
from src.dashboard.renderer import DashboardRenderer

settings = Settings()
renderer = DashboardRenderer(settings)

# Start persistent browser
success = renderer.start_persistent_browser(settings.dakboard_url)
print(f'Browser started: {success}')

# Take screenshot
if success:
    image = renderer.render_persistent_screenshot()
    print(f'Screenshot taken: {image is not None}')
    
# Clean up
renderer.cleanup_persistent_browser()
"
```

## Performance Monitoring

The Pi Home Dashboard includes comprehensive performance monitoring using **Grafana Cloud** for cloud-hosted dashboards, advanced alerting, and long-term data retention.

### Key Metrics Monitored

- **Render Performance**: Dashboard rendering times (persistent browser vs standard)
- **Display Performance**: E-ink display update times (partial vs full refresh)
- **Browser Memory**: Memory usage of Chromium and Playwright processes
- **Success Rates**: Overall, render, and display success rates
- **System Health**: CPU temperature, memory usage, disk usage, network stats
- **Service Status**: Dashboard service and component availability

### Setup Grafana Cloud Monitoring

```bash
# Set your Grafana Cloud credentials
export GRAFANA_CLOUD_PROMETHEUS_URL='https://prometheus-prod-XX-prod-us-west-0.grafana.net/api/prom/push'
export GRAFANA_CLOUD_PROMETHEUS_USER='your_prometheus_user_id'
export GRAFANA_CLOUD_PROMETHEUS_PASSWORD='your_grafana_cloud_api_key'

# Optional: For log collection
export GRAFANA_CLOUD_LOKI_URL='https://logs-prod-XXX.grafana.net/loki/api/v1/push'
export GRAFANA_CLOUD_LOKI_USER='your_loki_user_id'
export GRAFANA_CLOUD_LOKI_PASSWORD='your_grafana_cloud_api_key'

# Install and configure Grafana Alloy agent
./scripts/setup_grafana_cloud.sh
```

### Access Your Metrics

1. Go to [Grafana Cloud](https://grafana.com/)
2. Navigate to "Explore" and select your Prometheus data source
3. Query metrics with job labels:
   - `job="pi-home-dash"` (custom application metrics)
   - `job="integrations/raspberrypi-node"` (system metrics)

### Key Grafana Cloud Metrics

```promql
# Render performance
rate(pi_dashboard_render_duration_seconds_sum[5m]) / rate(pi_dashboard_render_duration_seconds_count[5m])

# Display update performance  
rate(pi_dashboard_display_update_duration_seconds_sum[5m]) / rate(pi_dashboard_display_update_duration_seconds_count[5m])

# Success rate
rate(pi_dashboard_updates_total{status="success"}[5m]) / rate(pi_dashboard_updates_total[5m]) * 100

# CPU temperature
node_hwmon_temp_celsius

# Memory usage
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100
```

### How It Works

The monitoring system uses **Prometheus metrics** with **Grafana Alloy agent**:

1. **Prometheus Instrumentation**: Application exposes metrics at `localhost:8000/metrics`
2. **Grafana Alloy Agent**: Collects metrics and system data, sends to Grafana Cloud
3. **Cloud Dashboards**: Professional visualizations accessible from anywhere

### Performance Targets

- **Render Time**: <5 seconds (persistent browser), <30 seconds (standard)
- **Display Update**: <2 seconds (partial refresh), <10 seconds (full refresh)
- **Success Rate**: >95% overall reliability
- **CPU Temperature**: <70°C to avoid throttling
- **Memory Usage**: <200MB browser memory for optimal performance

### Monitoring Features

- **Cloud-hosted dashboards** accessible from anywhere
- **Advanced alerting** with multiple notification channels
- **Long-term data retention** and historical analysis
- **Professional visualization** and query capabilities
- **Automatic Raspberry Pi integration** dashboards
- **System and application metrics** in unified interface

### Configuration Files

- **Grafana Alloy**: `/etc/alloy/config.alloy` (agent configuration)
- **Setup Script**: `scripts/setup_grafana_cloud.sh` (automated setup for fresh installations)
- **Service**: `sudo systemctl status alloy` (service management)
- **Logs**: `sudo journalctl -u alloy -f` (troubleshooting)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test changes with Docker emulation
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- [GregDMeyer/IT8951](https://github.com/GregDMeyer/IT8951) for enhanced e-ink display control with partial refresh support
- [netdata](https://www.netdata.cloud/) for real-time performance monitoring
- Waveshare for e-Paper display hardware and drivers
- DAKboard for dashboard inspiration
- lukechilds for Docker Pi virtualization
- Raspberry Pi Foundation for the computing platform
