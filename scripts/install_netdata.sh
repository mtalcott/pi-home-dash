#!/bin/bash

# Netdata Installation Script for Pi Home Dashboard
# Installs netdata with custom collectors for dashboard performance monitoring

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

# Install netdata
install_netdata() {
    log_info "Installing netdata..."
    
    # Download and run the official netdata installer
    bash <(curl -Ss https://my-netdata.io/kickstart.sh) --stable-channel --disable-telemetry
    
    # Enable and start netdata service
    sudo systemctl enable netdata
    sudo systemctl start netdata
    
    log_success "Netdata installed and started"
}

# Configure netdata for Pi Home Dashboard
configure_netdata() {
    log_info "Configuring netdata for Pi Home Dashboard monitoring..."
    
    # Create custom netdata configuration
    sudo tee /etc/netdata/netdata.conf > /dev/null << 'EOF'
# Pi Home Dashboard Netdata Configuration

[global]
    # Optimize for Raspberry Pi Zero 2 W
    memory mode = ram
    page cache size = 32
    dbengine multihost disk space = 256
    
    # Update intervals optimized for dashboard monitoring
    update every = 5
    
    # Web interface settings
    bind socket to IP = 0.0.0.0
    default port = 19999
    
    # Disable unnecessary features for Pi
    enable web responses gzip compression = no

[web]
    # Allow access from local network
    allow connections from = localhost 10.* 192.168.* 172.16.* 172.17.* 172.18.* 172.19.* 172.20.* 172.21.* 172.22.* 172.23.* 172.24.* 172.25.* 172.26.* 172.27.* 172.28.* 172.29.* 172.30.* 172.31.*
    
[plugins]
    # Enable Python plugins for custom collectors
    python.d = yes
    
    # Disable heavy plugins not needed for dashboard monitoring
    charts.d = no
    node.d = no
    apps = yes
    proc = yes
    diskspace = yes
    cgroups = yes
EOF

    log_success "Netdata configuration updated"
}

# Install Python dependencies for custom collectors
install_python_deps() {
    log_info "Installing Python dependencies for custom collectors..."
    
    # Install required Python packages for netdata collectors
    sudo pip3 install psutil requests pillow
    
    log_success "Python dependencies installed"
}

# Create custom collectors directory
setup_custom_collectors() {
    log_info "Setting up custom collectors directory..."
    
    # Create directory for custom collectors
    sudo mkdir -p /usr/libexec/netdata/python.d
    sudo mkdir -p /etc/netdata/python.d
    
    # Set proper permissions
    sudo chown -R netdata:netdata /usr/libexec/netdata/python.d
    sudo chown -R netdata:netdata /etc/netdata/python.d
    
    log_success "Custom collectors directory created"
}

# Configure firewall for netdata (if ufw is enabled)
configure_firewall() {
    if command -v ufw >/dev/null 2>&1 && sudo ufw status | grep -q "Status: active"; then
        log_info "Configuring firewall for netdata..."
        sudo ufw allow 19999/tcp comment "Netdata monitoring"
        log_success "Firewall configured for netdata"
    else
        log_info "UFW not active, skipping firewall configuration"
    fi
}

# Main installation function
main() {
    log_info "Starting netdata installation for Pi Home Dashboard..."
    
    check_root
    
    # Check if netdata is already installed
    if systemctl is-active --quiet netdata 2>/dev/null; then
        log_warning "Netdata is already installed and running"
        log_info "Reconfiguring for Pi Home Dashboard..."
    else
        install_netdata
    fi
    
    configure_netdata
    install_python_deps
    setup_custom_collectors
    configure_firewall
    
    # Restart netdata to apply configuration
    sudo systemctl restart netdata
    
    log_success "Netdata installation and configuration completed!"
    log_info "Access netdata dashboard at: http://$(hostname -I | awk '{print $1}'):19999"
    log_info "Custom Pi Home Dashboard collectors will be available after running setup_monitoring.sh"
}

# Run main function
main "$@"
