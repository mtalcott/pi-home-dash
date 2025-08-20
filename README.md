# Pi Home Dashboard - E-Ink Smart Calendar

A DIY e-ink display for home with smart calendar functionality, similar to Skylight Smart Calendar or DAKboard, powered by a Raspberry Pi Zero 2 W.

## Project Overview

This project creates a home smart calendar using:
- **Display**: Waveshare 10.3" e-Paper HAT (1872×1404, B&W)
- **Computer**: Raspberry Pi Zero 2 W
- **Features**: Calendar, weather, and to-do lists
- **Frame**: White shadow box frame for clean presentation
- **Testing**: Docker virtualization using lukechilds/dockerpi
- **Display Library**: omni-epd for simplified e-ink display control

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
- **omni-epd device**: `waveshare_epd.it8951`

### Frame Options
- 8×10" White Shadow Box Frame
- Interior depth: 1.5" (38mm) - sufficient for Pi and components
- Can stand in landscape orientation
- Fully enclosed back panel

## Software Architecture

### Core Components
1. **Dashboard Renderer**: Headless browser to render DAKboard or custom dashboard
2. **Display Driver**: Uses omni-epd library for simplified e-ink display control
3. **Scheduler**: Automated updates every few minutes
4. **Configuration**: Centralized settings management

### Display Library - omni-epd
This project uses the [omni-epd](https://github.com/robweber/omni-epd) library for e-ink display control:
- **Simplified API**: Abstract interface for multiple display types
- **Built-in Processing**: Automatic image conversion and dithering
- **Hardware Abstraction**: Works with or without physical hardware
- **Testing Support**: Mock display for development

### Data Sources
- DAKboard dashboard content (handles calendar, weather, todos, and custom widgets)

## GPIO SPI Connection

### Pi Zero 2 W to Waveshare 10.3" HAT
The omni-epd library handles the low-level SPI communication, but the physical connections are:

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
│   │   ├── eink_driver.py   # omni-epd wrapper for display control
│   │   └── image_processor.py # Additional image utilities (optional)
│   ├── config/
│   │   └── settings.py      # Configuration management
│   └── test/
│       ├── __init__.py      # Test package initialization
│       ├── integration_test.py # End-to-end integration tests
│       └── test_dashboard.html # HTML test file for dashboard rendering
├── test_setup.py           # Test setup and configuration
├── test_results/           # Test output directory (screenshots, reports, logs)
├── cache/                  # Cache directory for temporary files
├── logs/                   # Application logs directory
├── temp/                   # Temporary files directory
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose for testing
├── omni-epd.ini           # omni-epd display configuration
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
docker-compose run --rm pi-home-dash python src/main.py --integration-test --test-duration 60 --test-interval 3
```

### Integration Testing

The project includes comprehensive end-to-end integration tests that validate the complete pipeline from HTML rendering to virtual e-ink display updates:

```bash
# Run integration test with default settings (60s duration, 3s intervals)
docker-compose run --rm pi-home-dash python src/main.py --integration-test

# Custom test duration and intervals
docker-compose run --rm pi-home-dash python src/main.py --integration-test --test-duration 30 --test-interval 2

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
The display can be configured in `src/config/settings.py`:
```python
# omni-epd settings
epd_device = "waveshare_epd.it8951"  # Device type for 10.3" display
epd_mode = "bw"  # Display mode: "bw" or "gray16"
```

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

## omni-epd Integration

### Benefits
- **Simplified Code**: No need for custom SPI communication
- **Hardware Abstraction**: Works with or without physical display
- **Built-in Features**: Automatic image processing, dithering, rotation
- **Testing Support**: Mock display for development
- **Multiple Display Support**: Easy to switch between display types

### Configuration Options
The omni-epd library supports configuration via `.ini` files:

Create `omni-epd.ini` in the project root:
```ini
[EPD]
type=waveshare_epd.it8951
mode=bw

[Display]
rotate=0
flip_horizontal=False
flip_vertical=False

[Image Enhancements]
contrast=1
brightness=1
```

## Troubleshooting

### Common Issues
- **Display not updating**: Check SPI connection and enable SPI in raspi-config
- **omni-epd import error**: Install with `pip install omni-epd`
- **Slow rendering**: Ensure sufficient power supply (5V/2.5A minimum)
- **Ghosting on display**: Perform full refresh periodically
- **Network issues**: Check Wi-Fi configuration and DAKboard URL accessibility

### Debug Commands
```bash
# Test omni-epd installation
omni-epd-test -e waveshare_epd.it8951

# Check SPI interface
ls /dev/spi*

# Test GPIO connections (if needed)
gpio readall

# Monitor system logs
journalctl -u pi-dashboard -f

# Run with debug logging
docker-compose run --rm pi-home-dash python src/main.py --debug
```

### Display Testing
```bash
# Test with omni-epd utility
omni-epd-test -e waveshare_epd.it8951

# Test with project
docker-compose run --rm pi-home-dash python src/main.py --test

# List available display types
omni-epd-test --list
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test changes with Docker emulation
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- [omni-epd](https://github.com/robweber/omni-epd) for simplified e-ink display control
- Waveshare for e-Paper display hardware and drivers
- DAKboard for dashboard inspiration
- lukechilds for Docker Pi virtualization
- Raspberry Pi Foundation for the computing platform
