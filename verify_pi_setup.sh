#!/bin/bash

# Pi Home Dashboard Hardware Verification Script
# Run this script on the Raspberry Pi to verify SPI and omni-epd setup

# Don't exit on errors - we want to run all checks and report results
set +e

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

# Check SPI devices
check_spi_devices() {
    log_info "Checking SPI devices..."
    
    if ls /dev/spidev* >/dev/null 2>&1; then
        log_success "SPI devices found:"
        ls -l /dev/spidev*
    else
        log_error "No SPI devices found. SPI may not be enabled."
        log_info "Enable SPI with: sudo raspi-config"
        log_info "Or add 'dtparam=spi=on' to /boot/config.txt and reboot"
        return 1
    fi
}

# Check user groups
check_user_groups() {
    log_info "Checking user groups..."
    
    if groups $USER | grep -q spi; then
        log_success "User $USER is in the spi group"
        return 0
    else
        log_warning "User $USER is not in the spi group"
        log_info "Add user to spi group with: sudo usermod -aG spi $USER"
        log_info "Then log out and back in (or reboot)"
        return 1
    fi
}

# Check SPI configuration
check_spi_config() {
    log_info "Checking SPI configuration..."
    
    if command -v raspi-config >/dev/null 2>&1; then
        spi_status=$(sudo raspi-config nonint get_spi)
        if [ "$spi_status" = "0" ]; then
            log_success "SPI is enabled in raspi-config"
        else
            log_error "SPI is disabled in raspi-config"
            log_info "Enable with: sudo raspi-config nonint do_spi 0"
            return 1
        fi
    else
        log_warning "raspi-config not available, checking /boot/config.txt"
        if grep -q "^dtparam=spi=on" /boot/config.txt; then
            log_success "SPI enabled in /boot/config.txt"
        else
            log_error "SPI not enabled in /boot/config.txt"
            return 1
        fi
    fi
}

# Test omni-epd library
test_omni_epd() {
    log_info "Testing omni-epd library..."
    
    # Check if we're in the project directory
    if [ ! -f "requirements.txt" ] || [ ! -d "venv" ]; then
        log_error "Not in pi-home-dash directory or venv not found"
        log_info "Run this script from the pi-home-dash directory after setup"
        return 1
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Test mock display first
    log_info "Testing mock display..."
    if python -c "
from omni_epd import displayfactory
d = displayfactory.load_display_driver('omni_epd.mock')
print(f'Mock display: {d.width}x{d.height}')
d.prepare()
print('Mock display test passed')
" 2>/dev/null; then
        log_success "Mock display test passed"
    else
        log_error "Mock display test failed"
        return 1
    fi
    
    # Test real hardware display
    log_info "Testing real hardware display..."
    if OMNI_EPD_DISPLAY=waveshare_epd.it8951 python -c "
from omni_epd import displayfactory
import PIL.Image as Image
try:
    d = displayfactory.load_display_driver('waveshare_epd.it8951')
    print(f'Hardware display: {d.width}x{d.height}')
    d.prepare()
    # Create a simple white image and display it
    img = Image.new('L', (d.width, d.height), 255)
    d.display(img)
    d.sleep()
    print('Hardware display test passed')
except Exception as e:
    print(f'Hardware display test failed: {e}')
    raise
" 2>/dev/null; then
        log_success "Hardware display test passed"
    else
        log_error "Hardware display test failed"
        log_info "This could be due to:"
        log_info "  - SPI not enabled or accessible"
        log_info "  - User not in spi group"
        log_info "  - Hardware connection issues"
        log_info "  - Missing permissions"
        return 1
    fi
}

# Test application with real hardware
test_app_hardware() {
    log_info "Testing application with real hardware..."
    
    if [ ! -f "src/main.py" ]; then
        log_error "src/main.py not found"
        return 1
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Test with hardware display
    if OMNI_EPD_DISPLAY=waveshare_epd.it8951 python src/main.py --test; then
        log_success "Application hardware test passed"
    else
        log_error "Application hardware test failed"
        return 1
    fi
}

# Main verification function
main() {
    log_info "Starting Pi Home Dashboard hardware verification..."
    echo
    
    # Run all checks
    checks_passed=0
    total_checks=5
    
    if check_spi_devices; then
        ((checks_passed++))
    fi
    echo
    
    if check_user_groups; then
        ((checks_passed++))
    fi
    echo
    
    if check_spi_config; then
        ((checks_passed++))
    fi
    echo
    
    if test_omni_epd; then
        ((checks_passed++))
    fi
    echo
    
    if test_app_hardware; then
        ((checks_passed++))
    fi
    echo
    
    # Summary
    log_info "Verification Summary:"
    log_info "Checks passed: $checks_passed/$total_checks"
    
    if [ $checks_passed -eq $total_checks ]; then
        log_success "All verification checks passed!"
        log_info "Your Pi is ready to run the dashboard with real hardware"
        log_info "Start the service with: sudo systemctl start pi-home-dash"
    else
        log_warning "Some verification checks failed"
        log_info "Please address the issues above before running the dashboard"
        exit 1
    fi
}

# Run main function
main "$@"
