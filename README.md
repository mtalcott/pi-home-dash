# Pi Home Dashboard - E-Ink Smart Display

A DIY e-ink display for home with smart calendar functionality, similar to Skylight Smart Calendar or DAKboard. It runs on a Raspberry Pi 4 and renders a customizable dashboard (calendar, weather, to-do lists) onto a 10.3" e-paper screen, designed to be mounted in a shadow box frame.

<img width="1660" height="1240" alt="pi-home-dash-rendered" src="https://github.com/user-attachments/assets/8a8c1737-790f-4f3c-8126-4c3da023062b" />

## Hardware Components

### Required Parts
- **Display**: Waveshare 10.3" e-Paper HAT (Model: IT8951 Controller, 1872×1404 Resolution) - ~$200
- **Computer**: Raspberry Pi 4 Model B (2GB RAM or higher recommended) - ~$55
- **Power**: 5V/3A USB-C Power Supply (Official Raspberry Pi PSU recommended)
- **Storage**: 16GB+ Class 10 MicroSD Card
- **Frame**: 8×10" Shadow Box (1.5" depth minimum)
- **Cables**: Micro HDMI to HDMI Adapter (for initial setup/debugging)

## Software Architecture

### Core Stack
- **Dashboard Renderer**: Headless Chromium (Playwright) rendering DAKboard or custom HTML.
- **Display Driver**: Python interface for the IT8951 controller, utilizing the [GregDMeyer/IT8951](https://github.com/GregDMeyer/IT8951) library for direct hardware access and partial refresh capability.
- **Orchestration**: Docker Compose for development and testing.

### Key Features
1. **Persistent Browser**: Keeps a background Chromium instance running to significantly reduce render latency. 
2. **Dual Refresh Modes**: Switches between partial updates (for clock/time) and full refreshes (to clear ghosting).
3. **Resilience**: Automatic failure recovery and daily browser restarts to maintain system health.

## Installation

### Quick Setup (Raspberry Pi)
For a fresh Raspberry Pi 4 Model B running Raspberry Pi OS (64-bit recommended):

```bash
# Installs dependencies, creates virtual env, sets up systemd service, and tests the installation

curl -sSL https://raw.githubusercontent.com/mtalcott/pi-home-dash/master/install.sh | bash
```

### Manual Setup

Alternatively:

```bash
# Clone repository
git clone <repository-url> ~/pi-home-dash
cd ~/pi-home-dash

# Run setup script
chmod +x setup_pi.sh
./setup_pi.sh
```

### Post-Install Configuration

1. Edit `~/pi-home-dash/.env` with your settings (see **Configuration** below).
2. Reboot: `sudo reboot` (Required to enable SPI).
3. Service runs automatically. Check status: `sudo systemctl status pi-home-dash`.

## Configuration

### Key Settings

| Variable | Description | Default |
| --- | --- | --- |
| `DAKBOARD_URL` | URL of the dashboard to display | (Required) |
| `UPDATE_INTERVAL` | Seconds between screen updates | `300` |
| `DEBUG` | Enable verbose logging | `false` |

## Usage & Development

This project uses **Docker Compose** for consistent development and testing environments.

### Common Commands

**Run Application:**

```bash
# Build the image
docker-compose build

# Run once and exit (Single update)
docker-compose run --rm pi-home-dash python src/main.py --update

# Run in continuous mode (production-like)
docker-compose run --rm pi-home-dash python src/main.py --continuous
```

**Testing and Debugging:**

```bash
# Build the image
docker-compose build

# Run single test (default command)
docker-compose run --rm pi-home-dash python src/main.py --test

# Run with debug logging
docker-compose run --rm pi-home-dash python src/main.py --debug --test

# Run integration tests (HTML -> Image -> Mock Display) with default settings (60s duration, 3s intervals)
docker-compose run --rm pi-home-dash python src/main.py --integration-test

# Custom test duration and intervals
docker-compose run --rm pi-home-dash python src/main.py --integration-test --duration 30 --interval 2

# With artifact collection and validation
docker-compose run --rm pi-home-dash python src/main.py --integration-test --collect-artifacts

# Run in continuous mode (production-like) with custom environment variables
DEBUG=false DAKBOARD_URL=https://dakboard.com/display/uuid/DAKBOARD_UUID docker-compose run --rm pi-home-dash python src/main.py --continuous

# Run background service with restart policy
docker-compose up -d --restart unless-stopped pi-home-dash

# View logs
docker-compose logs -f pi-home-dash

# Stop services
docker-compose down
```

## Performance Monitoring

The dashboard exposes Prometheus metrics for monitoring via Grafana Cloud.

### Setup

```bash
# Set credentials in environment
export GRAFANA_CLOUD_PROMETHEUS_URL='...'
export GRAFANA_CLOUD_PROMETHEUS_USER='...'
export GRAFANA_CLOUD_PROMETHEUS_PASSWORD='...'

# Run setup script
./scripts/setup_grafana_cloud.sh
```

### Metrics

* **Render Time**: Tracks how long the headless browser takes to capture screenshots.
* **Display Update Time**: Tracks data transfer speed to the e-ink HAT.
* **System Health**: CPU temp, RAM usage.

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Submit a Pull Request.

## License

MIT License - see LICENSE file.

## Acknowledgments

* [GregDMeyer/IT8951](https://github.com/GregDMeyer/IT8951) for the e-ink driver implementation.
