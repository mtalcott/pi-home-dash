#!/bin/bash

# Pi Home Dashboard Setup Script
# This script sets up the Pi Home Dashboard on a real Raspberry Pi
# Extracted from Dockerfile to keep setup DRY between Docker and Pi environments

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Check if running on Raspberry Pi
check_pi() {
    if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        log_warning "This doesn't appear to be a Raspberry Pi. Continuing anyway..."
    else
        log_info "Detected Raspberry Pi hardware"
    fi
}

# Update system packages
update_system() {
    log_info "Updating system packages..."
    sudo apt-get update
    log_success "System packages updated"
}

# Install system dependencies using shared function
install_system_deps() {
    log_info "Installing system dependencies..."
    
    # Source the common setup functions
    source "$HOME/pi-home-dash/scripts/common_setup.sh"
    
    # Use shared function for Pi-specific dependencies
    install_pi_system_deps
    
    log_success "System dependencies installed"
}

# Enable SPI interface (required for e-ink display)
enable_spi() {
    log_info "Enabling SPI interface..."
    
    if ! grep -q "^dtparam=spi=on" /boot/config.txt; then
        echo "dtparam=spi=on" | sudo tee -a /boot/config.txt
        log_warning "SPI enabled. A reboot will be required after setup."
    else
        log_info "SPI already enabled"
    fi
}

# Create project directory structure using shared function
create_directories() {
    log_info "Creating project directories..."
    
    # Source the common setup functions
    source "$HOME/pi-home-dash/scripts/common_setup.sh"
    
    # Use shared function for directory creation
    create_common_directories "$HOME/pi-home-dash"
    
    log_success "Project directories created"
}

# Setup Python virtual environment using shared function
setup_python_env() {
    log_info "Setting up Python virtual environment..."
    
    cd "$HOME/pi-home-dash"
    
    # Create virtual environment
    python3 -m venv venv
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies from requirements.txt
    if pip install --no-cache-dir -r requirements.txt; then
        log_info "Installing Playwright Chromium browser..."
        if playwright install chromium; then
            log_info "Fixing GPIO library conflicts..."
            # Fix GPIO library conflicts that can cause hardware initialization errors
            python3 -m pip uninstall -y Jetson.GPIO 2>/dev/null || true
            python -m pip install --upgrade --force-reinstall \
                adafruit-blinka Adafruit-PlatformDetect Adafruit-PureIO
            pip install --force-reinstall RPi.GPIO
            log_success "Python environment, Playwright Chromium, and GPIO libraries setup complete"
        else
            log_error "Playwright Chromium installation failed"
            exit 1
        fi
    else
        log_error "Python environment setup failed"
        exit 1
    fi
}

# Setup environment variables (from Dockerfile)
setup_environment() {
    log_info "Setting up environment variables..."
    
    # Create environment file if it doesn't exist
    if [[ ! -f "$HOME/pi-home-dash/.env" ]]; then
        if [[ -f "$HOME/pi-home-dash/.env.example" ]]; then
            cp "$HOME/pi-home-dash/.env.example" "$HOME/pi-home-dash/.env"
            log_info "Created .env file from .env.example"
        else
            # Create basic .env file with Dockerfile defaults
            cat > "$HOME/pi-home-dash/.env" << EOF
# Pi Home Dashboard Environment Configuration
PYTHONPATH=$HOME/pi-home-dash/src
DISPLAY=:0
DEBUG=false
OMNI_EPD_DISPLAY=waveshare_epd.it8951
UPDATE_INTERVAL=60
DAKBOARD_URL=https://dakboard.com/screen/your-screen-id
EOF
            log_info "Created basic .env file"
        fi
        
        log_warning "Please edit $HOME/pi-home-dash/.env to configure your settings"
    fi
    
    # Add environment variables to .bashrc for persistence
    if ! grep -q "pi-home-dash" "$HOME/.bashrc"; then
        cat >> "$HOME/.bashrc" << EOF

# Pi Home Dashboard Environment
export PYTHONPATH="$HOME/pi-home-dash/src:\$PYTHONPATH"
alias pi-dash="cd $HOME/pi-home-dash && source venv/bin/activate"
EOF
        log_info "Added environment variables to .bashrc"
    fi
}

# Setup log rotation
setup_log_rotation() {
    log_info "Setting up log rotation..."
    
    # Create logrotate configuration for pi-home-dash
    sudo tee /etc/logrotate.d/pi-home-dash > /dev/null << EOF
$HOME/pi-home-dash/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 $USER $USER
    postrotate
        # Send SIGUSR1 to the application to reopen log files if needed
        systemctl reload-or-restart pi-home-dash.service > /dev/null 2>&1 || true
    endscript
}
EOF
    
    # Test the logrotate configuration
    if sudo logrotate -d /etc/logrotate.d/pi-home-dash > /dev/null 2>&1; then
        log_success "Log rotation configuration created and tested"
    else
        log_warning "Log rotation configuration created but test failed"
    fi
}

# Create systemd service for automatic startup
create_systemd_service() {
    log_info "Creating systemd service..."
    
    # Create systemd service file
    sudo tee /etc/systemd/system/pi-home-daseh.service > /dev/null << EOF
[Unit]
Description=Pi Home Dashboard
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/pi-home-dash
Environment=OMNI_EPD_DISPLAY=waveshare_epd.it8951
EnvironmentFile=$HOME/pi-home-dash/.env
ExecStart=$HOME/pi-home-dash/venv/bin/python src/main.py --continuous
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable pi-home-dash.service
    
    log_success "Systemd service created and enabled"
}

# Test the installation
test_installation() {
    log_info "Testing installation..."
    
    cd "$HOME/pi-home-dash"
    source venv/bin/activate
    
    # Test basic functionality
    if python src/main.py --test; then
        log_success "Installation test passed"
    else
        log_error "Installation test failed"
        return 1
    fi
}

# Main setup function
main() {
    log_info "Starting Pi Home Dashboard setup..."
    
    check_root
    check_pi
    
    # Check if project directory exists
    if [[ ! -d "$HOME/pi-home-dash" ]]; then
        log_error "Project directory $HOME/pi-home-dash not found."
        log_info "Please clone the repository first:"
        log_info "  git clone <repository-url> $HOME/pi-home-dash"
        exit 1
    fi
    
    update_system
    install_system_deps
    enable_spi
    create_directories
    setup_python_env
    setup_environment
    setup_log_rotation
    create_systemd_service
    
    log_success "Setup completed successfully!"
    
    # Test installation
    if test_installation; then
        log_info "Next steps:"
        log_info "1. Edit $HOME/pi-home-dash/.env to configure your DAKboard URL"
        log_info "2. Reboot the Pi to enable SPI: sudo reboot"
        log_info "3. After reboot, start the service: sudo systemctl start pi-home-dash"
        log_info "4. Check service status: sudo systemctl status pi-home-dash"
        log_info "5. View logs: journalctl -u pi-home-dash -f"
    else
        log_error "Setup completed but tests failed. Please check the logs."
        exit 1
    fi
}

# Run main function
main "$@"
