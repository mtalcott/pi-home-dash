#!/bin/bash

# Pi Home Dashboard Monitoring Setup Script
# Sets up netdata with custom collectors for performance monitoring

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root. Please run as a regular user."
        log_info "The script will use sudo when needed."
        exit 1
    fi
}

# Get project root directory
get_project_root() {
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    
    if [[ ! -f "$PROJECT_ROOT/src/main.py" ]]; then
        log_error "Cannot find Pi Home Dashboard project root"
        log_info "Please run this script from the scripts directory within the project"
        exit 1
    fi
    
    log_info "Project root: $PROJECT_ROOT"
}

# Install netdata if not already installed
install_netdata() {
    if ! command -v netdata >/dev/null 2>&1; then
        log_info "Netdata not found, installing..."
        bash "$PROJECT_ROOT/scripts/install_netdata.sh"
    else
        log_info "Netdata already installed"
    fi
}

# Setup custom collector
setup_custom_collector() {
    log_info "Setting up Pi Dashboard custom collector..."
    
    # Copy the custom collector to netdata's python.d directory
    sudo cp "$PROJECT_ROOT/monitoring/collectors/pi_dashboard.py" /usr/libexec/netdata/python.d/
    sudo chown netdata:netdata /usr/libexec/netdata/python.d/pi_dashboard.py
    sudo chmod 755 /usr/libexec/netdata/python.d/pi_dashboard.py
    
    # Create collector configuration
    sudo tee /etc/netdata/python.d/pi_dashboard.conf > /dev/null << EOF
# Pi Home Dashboard Custom Collector Configuration

# Enable the collector
pi_dashboard: yes

# Update interval (seconds)
update_every: 5

# Priority (lower numbers = higher priority)
priority: 60000

# Retries on failure
retries: 60
EOF
    
    sudo chown netdata:netdata /etc/netdata/python.d/pi_dashboard.conf
    
    log_success "Custom collector installed"
}

# Create monitoring dashboard configuration
create_dashboard_config() {
    log_info "Creating monitoring dashboard configuration..."
    
    # Create custom dashboard configuration for Pi Home Dashboard
    sudo tee /etc/netdata/health.d/pi_dashboard.conf > /dev/null << 'EOF'
# Pi Home Dashboard Health Monitoring

# Alert if render time is too high (> 30 seconds)
 alarm: pi_dashboard_render_time_high
    on: pi_dashboard.render_performance.render_time_avg
 every: 30s
  warn: $this > 30000
  crit: $this > 60000
  info: Dashboard render time is too high
    to: sysadmin

# Alert if success rate drops below threshold
 alarm: pi_dashboard_success_rate_low
    on: pi_dashboard.success_rate.success_rate
 every: 60s
  warn: $this < 90
  crit: $this < 75
  info: Dashboard success rate is below acceptable threshold
    to: sysadmin

# Alert if service is not running
 alarm: pi_dashboard_service_down
    on: pi_dashboard.dashboard_status.service_running
 every: 30s
  crit: $this == 0
  info: Pi Home Dashboard service is not running
    to: sysadmin

# Alert if display is disconnected
 alarm: pi_dashboard_display_disconnected
    on: pi_dashboard.dashboard_status.display_connected
 every: 60s
  warn: $this == 0
  info: E-ink display appears to be disconnected
    to: sysadmin

# Alert if CPU temperature is too high
 alarm: pi_dashboard_cpu_temp_high
    on: pi_dashboard.system_health.cpu_temp
 every: 30s
  warn: $this > 70
  crit: $this > 80
  info: Raspberry Pi CPU temperature is high
    to: sysadmin

# Alert if memory usage is too high
 alarm: pi_dashboard_memory_high
    on: pi_dashboard.system_health.memory_usage
 every: 60s
  warn: $this > 80
  crit: $this > 90
  info: System memory usage is high
    to: sysadmin

# Alert if browser memory usage is excessive
 alarm: pi_dashboard_browser_memory_high
    on: pi_dashboard.browser_memory.total_browser_memory
 every: 60s
  warn: $this > 200
  crit: $this > 400
  info: Browser memory usage is excessive
    to: sysadmin
EOF
    
    sudo chown netdata:netdata /etc/netdata/health.d/pi_dashboard.conf
    
    log_success "Health monitoring configuration created"
}

# Create systemd service for metrics collection
create_metrics_service() {
    log_info "Creating metrics collection service..."
    
    # Create a simple service to ensure metrics directory exists and has proper permissions
    sudo tee /etc/systemd/system/pi-dashboard-metrics.service > /dev/null << EOF
[Unit]
Description=Pi Home Dashboard Metrics Setup
After=pi-home-dash.service
Requires=pi-home-dash.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=root
ExecStart=/bin/bash -c 'mkdir -p $PROJECT_ROOT/cache && chown -R $USER:$USER $PROJECT_ROOT/cache && chmod 755 $PROJECT_ROOT/cache'
ExecStart=/bin/bash -c 'mkdir -p $PROJECT_ROOT/logs && chown -R $USER:$USER $PROJECT_ROOT/logs && chmod 755 $PROJECT_ROOT/logs'

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable pi-dashboard-metrics.service
    
    log_success "Metrics service created"
}

# Test the monitoring setup
test_monitoring() {
    log_info "Testing monitoring setup..."
    
    # Test if netdata is running
    if systemctl is-active --quiet netdata; then
        log_success "Netdata service is running"
    else
        log_error "Netdata service is not running"
        return 1
    fi
    
    # Test if custom collector is loaded
    sleep 5  # Give netdata time to load collectors
    
    if curl -s "http://localhost:19999/api/v1/charts" | grep -q "pi_dashboard"; then
        log_success "Pi Dashboard collector is loaded"
    else
        log_warning "Pi Dashboard collector not yet loaded (may take a few minutes)"
    fi
    
    # Test if metrics file can be created
    if touch "$PROJECT_ROOT/cache/metrics.json" 2>/dev/null; then
        log_success "Metrics file location is writable"
        rm -f "$PROJECT_ROOT/cache/metrics.json"
    else
        log_error "Cannot write to metrics file location"
        return 1
    fi
    
    return 0
}

# Create monitoring documentation
create_documentation() {
    log_info "Creating monitoring documentation..."
    
    cat > "$PROJECT_ROOT/MONITORING.md" << 'EOF'
# Pi Home Dashboard Monitoring

This document describes the monitoring setup for the Pi Home Dashboard using netdata.

## Overview

The monitoring system tracks key performance metrics:

### Performance Metrics
- **Render Performance**: Dashboard rendering times (persistent browser vs standard)
- **Display Performance**: E-ink display update times (full vs partial refresh)
- **Browser Memory**: Memory usage of Chromium and Playwright processes
- **Update Frequency**: Actual vs expected update frequency
- **Success Rates**: Overall, render, and display success rates

### System Health
- **CPU Temperature**: Raspberry Pi CPU temperature monitoring
- **Throttling Events**: CPU throttling detection
- **Memory Usage**: System memory utilization
- **Disk Usage**: Storage utilization

### Service Status
- **Service Running**: Pi Home Dashboard service status
- **Persistent Browser**: Browser process status
- **Display Connected**: E-ink display connection status
- **Network Connected**: Internet connectivity status

## Accessing Monitoring

### Netdata Dashboard
Access the monitoring dashboard at: `http://your-pi-ip:19999`

### Key Charts
- **Pi Dashboard > Render Performance**: Rendering time metrics
- **Pi Dashboard > Display Performance**: E-ink update times
- **Pi Dashboard > Browser Memory**: Memory usage tracking
- **Pi Dashboard > Success Rate**: Reliability metrics
- **Pi Dashboard > System Health**: Temperature and resource usage
- **Pi Dashboard > Service Status**: Service availability

### Mobile Access
The netdata dashboard is mobile-friendly and can be accessed from phones/tablets.

## Alerts

Health monitoring alerts are configured for:

- High render times (>30s warning, >60s critical)
- Low success rates (<90% warning, <75% critical)
- Service downtime
- Display disconnection
- High CPU temperature (>70°C warning, >80°C critical)
- High memory usage (>80% warning, >90% critical)
- Excessive browser memory usage (>200MB warning, >400MB critical)

## Performance Optimization

### Key Metrics to Monitor

1. **Render Delay**: Target <5 seconds for persistent browser, <30 seconds for standard
2. **Display Update Time**: Target <2 seconds for partial refresh, <10 seconds for full
3. **Success Rate**: Target >95% overall success rate
4. **Memory Usage**: Keep browser memory <200MB for optimal performance
5. **CPU Temperature**: Keep below 70°C to avoid throttling

### Troubleshooting

#### High Render Times
- Check network connectivity
- Verify DAKboard URL accessibility
- Consider browser restart if persistent browser is slow

#### Display Update Failures
- Check SPI connection
- Verify display power
- Check for GPIO conflicts

#### High Memory Usage
- Restart persistent browser daily (automatic)
- Monitor for memory leaks
- Consider reducing browser cache

#### CPU Throttling
- Improve cooling/ventilation
- Reduce update frequency during hot weather
- Monitor power supply adequacy

## Log Files

- Application logs: `/var/log/pi-dashboard.log` or `~/pi-home-dash/logs/`
- Netdata logs: `/var/log/netdata/`
- System logs: `journalctl -u pi-home-dash`

## Configuration Files

- Netdata config: `/etc/netdata/netdata.conf`
- Custom collector: `/usr/libexec/netdata/python.d/pi_dashboard.py`
- Health alerts: `/etc/netdata/health.d/pi_dashboard.conf`
- Metrics data: `~/pi-home-dash/cache/metrics.json`
EOF
    
    log_success "Monitoring documentation created: $PROJECT_ROOT/MONITORING.md"
}

# Main setup function
main() {
    log_info "Setting up Pi Home Dashboard monitoring..."
    
    check_root
    get_project_root
    
    install_netdata
    setup_custom_collector
    create_dashboard_config
    create_metrics_service
    create_documentation
    
    # Restart netdata to load new configuration
    log_info "Restarting netdata to load new configuration..."
    sudo systemctl restart netdata
    
    # Start metrics service
    sudo systemctl start pi-dashboard-metrics.service
    
    # Wait a moment for services to start
    sleep 3
    
    if test_monitoring; then
        log_success "Monitoring setup completed successfully!"
        log_info ""
        log_info "Next steps:"
        log_info "1. Access netdata dashboard at: http://$(hostname -I | awk '{print $1}'):19999"
        log_info "2. Look for 'Pi Dashboard' section in the dashboard"
        log_info "3. Review monitoring documentation: $PROJECT_ROOT/MONITORING.md"
        log_info "4. Run the dashboard to start collecting metrics: sudo systemctl start pi-home-dash"
        log_info ""
        log_info "Key performance metrics to monitor:"
        log_info "- Render delay (target: <5s persistent browser, <30s standard)"
        log_info "- Display update time (target: <2s partial, <10s full refresh)"
        log_info "- Success rate (target: >95%)"
        log_info "- CPU temperature (keep <70°C)"
    else
        log_error "Monitoring setup completed but some tests failed"
        log_info "Check the logs and try restarting netdata: sudo systemctl restart netdata"
        exit 1
    fi
}

# Run main function
main "$@"
