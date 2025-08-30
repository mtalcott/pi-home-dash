#!/bin/bash

# Pi Home Dashboard Grafana Cloud Monitoring Setup Script
# Sets up Grafana Alloy agent with Grafana Cloud integration for metrics and logs

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

# Check for required Grafana Cloud credentials
check_credentials() {
    log_info "Checking Grafana Cloud credentials..."
    
    # Check if credentials are provided as environment variables
    if [[ -z "$GRAFANA_CLOUD_PROMETHEUS_URL" ]] || [[ -z "$GRAFANA_CLOUD_PROMETHEUS_USER" ]] || [[ -z "$GRAFANA_CLOUD_PROMETHEUS_PASSWORD" ]]; then
        log_error "Missing Grafana Cloud credentials!"
        log_info ""
        log_info "Please set the following environment variables:"
        log_info "export GRAFANA_CLOUD_PROMETHEUS_URL='https://prometheus-prod-XX-prod-us-west-0.grafana.net/api/prom/push'"
        log_info "export GRAFANA_CLOUD_PROMETHEUS_USER='your_prometheus_user_id'"
        log_info "export GRAFANA_CLOUD_PROMETHEUS_PASSWORD='your_grafana_cloud_api_key'"
        log_info ""
        log_info "Optional (for logs):"
        log_info "export GRAFANA_CLOUD_LOKI_URL='https://logs-prod-XXX.grafana.net/loki/api/v1/push'"
        log_info "export GRAFANA_CLOUD_LOKI_USER='your_loki_user_id'"
        log_info "export GRAFANA_CLOUD_LOKI_PASSWORD='your_grafana_cloud_api_key'"
        log_info ""
        log_info "You can find these credentials in your Grafana Cloud account under 'Connections' -> 'Add new connection' -> 'Hosted Prometheus metrics'"
        exit 1
    fi
    
    log_success "Grafana Cloud credentials found"
}

# Install Grafana Alloy
install_alloy() {
    if command -v alloy >/dev/null 2>&1; then
        log_info "Grafana Alloy already installed"
        return 0
    fi
    
    log_info "Installing Grafana Alloy..."
    
    # Detect architecture
    ARCH=$(uname -m)
    case $ARCH in
        x86_64)
            ARCH="amd64"
            ;;
        aarch64|arm64)
            ARCH="arm64"
            ;;
        armv7l)
            ARCH="armv7"
            ;;
        *)
            log_error "Unsupported architecture: $ARCH"
            exit 1
            ;;
    esac
    
    log_info "Detected architecture: $ARCH"
    
    # Use the Grafana Cloud installation script
    log_info "Using Grafana Cloud installation script..."
    
    # Create temporary installation script
    cat > /tmp/install_alloy.sh << 'EOF'
#!/bin/bash
# Download and install Grafana Alloy
set -e

# Get latest release info
LATEST_RELEASE=$(curl -s https://api.github.com/repos/grafana/alloy/releases/latest | grep '"tag_name"' | cut -d'"' -f4)
VERSION=${LATEST_RELEASE#v}

echo "Installing Grafana Alloy version $VERSION"

# Download and install
case $(uname -m) in
    x86_64)
        ARCH="amd64"
        ;;
    aarch64|arm64)
        ARCH="arm64"
        ;;
    armv7l)
        ARCH="armv7"
        ;;
esac

# Download the deb package
DEB_URL="https://github.com/grafana/alloy/releases/download/v${VERSION}/alloy-${VERSION}-1.${ARCH}.deb"
wget -O /tmp/alloy.deb "$DEB_URL"

# Install the package
sudo dpkg -i /tmp/alloy.deb || sudo apt-get install -f -y

# Clean up
rm -f /tmp/alloy.deb

echo "Grafana Alloy installed successfully"
EOF
    
    chmod +x /tmp/install_alloy.sh
    bash /tmp/install_alloy.sh
    rm -f /tmp/install_alloy.sh
    
    log_success "Grafana Alloy installed"
}

# Create Alloy configuration
create_alloy_config() {
    log_info "Creating Alloy configuration..."
    
    # Create the configuration directory if it doesn't exist
    sudo mkdir -p /etc/alloy
    
    # Create the main configuration file
    sudo tee /etc/alloy/config.alloy > /dev/null << EOF
// Prometheus remote write endpoint
prometheus.remote_write "metrics_service" {
	endpoint {
		url = "${GRAFANA_CLOUD_PROMETHEUS_URL}"

		basic_auth {
			username = "${GRAFANA_CLOUD_PROMETHEUS_USER}"
			password = "${GRAFANA_CLOUD_PROMETHEUS_PASSWORD}"
		}
	}
}

// ==== RASPBERRY PI INTEGRATION ====

// Node exporter for Raspberry Pi integration
prometheus.exporter.unix "integrations_node_exporter" { }

discovery.relabel "integrations_node_exporter" {
	targets = prometheus.exporter.unix.integrations_node_exporter.targets

	rule {
		target_label = "instance"
		replacement  = constants.hostname
	}

	rule {
		target_label = "job"
		replacement  = "integrations/raspberrypi-node"
	}
}

prometheus.scrape "integrations_node_exporter" {
	targets    = discovery.relabel.integrations_node_exporter.output
	forward_to = [prometheus.relabel.integrations_node_exporter.receiver]
	job_name   = "integrations/node_exporter"
}

prometheus.relabel "integrations_node_exporter" {
	forward_to = [prometheus.remote_write.metrics_service.receiver]

	rule {
		source_labels = ["__name__"]
		regex         = "up|node_boot_time_seconds|node_cpu_seconds_total|node_disk_io_time_seconds_total|node_disk_io_time_weighted_seconds_total|node_disk_read_bytes_total|node_disk_written_bytes_total|node_filesystem_avail_bytes|node_filesystem_files|node_filesystem_files_free|node_filesystem_readonly|node_filesystem_size_bytes|node_hwmon_temp_celsius|node_load1|node_load15|node_load5|node_memory_Buffers_bytes|node_memory_Cached_bytes|node_memory_MemAvailable_bytes|node_memory_MemFree_bytes|node_memory_MemTotal_bytes|node_memory_Slab_bytes|node_memory_SwapTotal_bytes|node_network_receive_bytes_total|node_network_receive_drop_total|node_network_receive_errs_total|node_network_receive_packets_total|node_network_transmit_bytes_total|node_network_transmit_drop_total|node_network_transmit_errs_total|node_network_transmit_packets_total|node_os_info|node_systemd_unit_state|node_uname_info|node_vmstat_pgmajfault"
		action        = "keep"
	}
}

// ==== PI HOME DASHBOARD CUSTOM MONITORING ====

// Scrape pi-home-dash custom metrics from Prometheus endpoint
prometheus.scrape "pi_home_dash" {
	targets = [
		{"__address__" = "localhost:8000", "job" = "pi-home-dash", "instance" = "pi-home-dash"},
	]
	forward_to      = [prometheus.remote_write.metrics_service.receiver]
	scrape_interval = "15s"
	scrape_timeout  = "10s"
}
EOF

    # Add Loki configuration if credentials are provided
    if [[ -n "$GRAFANA_CLOUD_LOKI_URL" ]] && [[ -n "$GRAFANA_CLOUD_LOKI_USER" ]] && [[ -n "$GRAFANA_CLOUD_LOKI_PASSWORD" ]]; then
        log_info "Adding Loki log collection configuration..."
        
        sudo tee -a /etc/alloy/config.alloy > /dev/null << EOF

// ==== LOG COLLECTION ====

// Loki logs endpoint
loki.write "grafana_cloud_loki" {
	endpoint {
		url = "${GRAFANA_CLOUD_LOKI_URL}"

		basic_auth {
			username = "${GRAFANA_CLOUD_LOKI_USER}"
			password = "${GRAFANA_CLOUD_LOKI_PASSWORD}"
		}
	}
}

// Journal logs for Raspberry Pi integration
discovery.relabel "logs_integrations_integrations_node_exporter_journal_scrape" {
	targets = []

	rule {
		source_labels = ["__journal__systemd_unit"]
		target_label  = "unit"
	}

	rule {
		source_labels = ["__journal__boot_id"]
		target_label  = "boot_id"
	}

	rule {
		source_labels = ["__journal__transport"]
		target_label  = "transport"
	}

	rule {
		source_labels = ["__journal_priority_keyword"]
		target_label  = "level"
	}
}

loki.source.journal "logs_integrations_integrations_node_exporter_journal_scrape" {
	max_age       = "24h0m0s"
	relabel_rules = discovery.relabel.logs_integrations_integrations_node_exporter_journal_scrape.rules
	forward_to    = [loki.write.grafana_cloud_loki.receiver]
	labels        = {
		instance = constants.hostname,
		job      = "integrations/raspberrypi-node",
	}
}

// Scrape systemd journal for system logs
loki.source.journal "systemd_logs" {
	max_age = "12h"
	labels  = {
		job  = "systemd-journal",
		host = "pi-home-dash",
	}
	forward_to = [loki.write.grafana_cloud_loki.receiver]
}
EOF
    else
        log_warning "Loki credentials not provided, skipping log collection setup"
    fi
    
    # Set proper permissions
    sudo chown root:root /etc/alloy/config.alloy
    sudo chmod 644 /etc/alloy/config.alloy
    
    log_success "Alloy configuration created"
}

# Configure and start Alloy service
setup_alloy_service() {
    log_info "Setting up Alloy service..."
    
    # Enable and start the service
    sudo systemctl enable alloy
    sudo systemctl restart alloy
    
    # Wait a moment for the service to start
    sleep 3
    
    # Check if service is running
    if systemctl is-active --quiet alloy; then
        log_success "Alloy service is running"
    else
        log_error "Alloy service failed to start"
        log_info "Checking service status..."
        sudo systemctl status alloy --no-pager
        return 1
    fi
}

# Test the monitoring setup
test_monitoring() {
    log_info "Testing monitoring setup..."
    
    # Test if Alloy is running
    if systemctl is-active --quiet alloy; then
        log_success "Alloy service is running"
    else
        log_error "Alloy service is not running"
        return 1
    fi
    
    # Test if pi-home-dash metrics endpoint is accessible
    if curl -s http://localhost:8000/metrics | grep -q "pi_dashboard"; then
        log_success "Pi-home-dash metrics endpoint is accessible"
    else
        log_warning "Pi-home-dash metrics endpoint not accessible (dashboard may not be running)"
    fi
    
    # Test if Alloy metrics endpoint is accessible
    if curl -s http://localhost:12345/metrics | grep -q "alloy_build_info"; then
        log_success "Alloy metrics endpoint is accessible"
    else
        log_warning "Alloy metrics endpoint not accessible"
    fi
    
    # Check for recent metric sends
    SENT_BATCHES=$(curl -s http://localhost:12345/metrics | grep "prometheus_remote_storage_sent_batch_duration_seconds_count" | grep -o '[0-9]\+$' | head -1)
    if [[ -n "$SENT_BATCHES" ]] && [[ "$SENT_BATCHES" -gt 0 ]]; then
        log_success "Metrics are being sent to Grafana Cloud ($SENT_BATCHES batches sent)"
    else
        log_warning "No metrics sent to Grafana Cloud yet (this is normal for new installations)"
    fi
    
    return 0
}


# Main setup function
main() {
    log_info "Setting up Pi Home Dashboard Grafana Cloud monitoring..."
    
    check_root
    get_project_root
    check_credentials
    
    install_alloy
    create_alloy_config
    setup_alloy_service
    
    if test_monitoring; then
        log_success "Grafana Cloud monitoring setup completed successfully!"
        log_info ""
        log_info "Next steps:"
        log_info "1. Access your Grafana Cloud dashboard at: https://grafana.com/"
        log_info "2. Go to 'Explore' and select your Prometheus data source"
        log_info "3. Look for metrics with job labels:"
        log_info "   - job=\"pi-home-dash\" (custom application metrics)"
        log_info "   - job=\"integrations/raspberrypi-node\" (system metrics)"
        log_info "4. Create dashboards and alerts as needed"
        log_info ""
        log_info "Key metrics to monitor:"
        log_info "- pi_dashboard_render_duration_seconds (render performance)"
        log_info "- pi_dashboard_display_update_duration_seconds (display performance)"
        log_info "- pi_dashboard_updates_total (success/failure counts)"
        log_info "- node_hwmon_temp_celsius (CPU temperature)"
        log_info "- node_memory_MemAvailable_bytes (available memory)"
        log_info ""
        log_info "Configuration file: /etc/alloy/config.alloy"
        log_info "Service status: sudo systemctl status alloy"
        log_info "Service logs: sudo journalctl -u alloy -f"
    else
        log_error "Monitoring setup completed but some tests failed"
        log_info "Check the logs: sudo journalctl -u alloy -f"
        exit 1
    fi
}

# Show usage information
show_usage() {
    echo "Pi Home Dashboard Grafana Cloud Setup"
    echo ""
    echo "This script sets up Grafana Alloy agent to send metrics and logs to Grafana Cloud."
    echo ""
    echo "Required environment variables:"
    echo "  GRAFANA_CLOUD_PROMETHEUS_URL      - Your Grafana Cloud Prometheus push URL"
    echo "  GRAFANA_CLOUD_PROMETHEUS_USER     - Your Grafana Cloud Prometheus user ID"
    echo "  GRAFANA_CLOUD_PROMETHEUS_PASSWORD - Your Grafana Cloud API key"
    echo ""
    echo "Optional environment variables (for log collection):"
    echo "  GRAFANA_CLOUD_LOKI_URL            - Your Grafana Cloud Loki push URL"
    echo "  GRAFANA_CLOUD_LOKI_USER           - Your Grafana Cloud Loki user ID"
    echo "  GRAFANA_CLOUD_LOKI_PASSWORD       - Your Grafana Cloud API key"
    echo ""
    echo "Example usage:"
    echo "  export GRAFANA_CLOUD_PROMETHEUS_URL='https://prometheus-prod-36-prod-us-west-0.grafana.net/api/prom/push'"
    echo "  export GRAFANA_CLOUD_PROMETHEUS_USER='2648813'"
    echo "  export GRAFANA_CLOUD_PROMETHEUS_PASSWORD='glc_...'"
    echo "  ./setup_grafana_cloud.sh"
    echo ""
}

# Handle command line arguments
case "${1:-}" in
    -h|--help)
        show_usage
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
