#!/bin/bash

# Pi Home Dashboard Quick Install Script
# This script clones the repository and runs the setup

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

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
REPO_URL="https://github.com/mtalcott/pi-home-dash.git"
INSTALL_DIR="$HOME/pi-home-dash"

main() {
    log_info "Pi Home Dashboard Quick Install"
    log_info "==============================="
    
    # Check if git is installed
    if ! command -v git &> /dev/null; then
        log_error "Git is not installed. Please install git first:"
        log_info "  sudo apt update && sudo apt install -y git"
        exit 1
    fi
    
    # Clone repository if it doesn't exist
    if [[ ! -d "$INSTALL_DIR" ]]; then
        log_info "Cloning repository to $INSTALL_DIR..."
        git clone "$REPO_URL" "$INSTALL_DIR"
        log_success "Repository cloned"
    else
        log_info "Repository already exists at $INSTALL_DIR"
        log_info "Updating repository..."
        cd "$INSTALL_DIR"
        git pull
        log_success "Repository updated"
    fi
    
    # Make setup script executable
    chmod +x "$INSTALL_DIR/setup_pi.sh"
    
    # Run setup script
    log_info "Running setup script..."
    "$INSTALL_DIR/setup_pi.sh"
    
    log_success "Installation complete!"
}

main "$@"
