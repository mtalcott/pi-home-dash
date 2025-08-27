#!/bin/bash

# Pi Home Dashboard Hardware Verification Script
# Run this script on the Raspberry Pi to verify SPI and IT8951 setup

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

# Test IT8951 library
test_it8951() {
    log_info "Testing IT8951 library..."
    
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
    if DISPLAY_TYPE=mock python -c "
import sys
sys.path.insert(0, 'src')
from config.settings import Settings
from display.it8951_driver import IT8951Driver
try:
    settings = Settings()
    settings.display_type = 'mock'
    driver = IT8951Driver(settings)
    print(f'Mock display: {driver.width}x{driver.height}')
    print('Mock display test passed')
except Exception as e:
    print(f'Mock display test failed: {e}')
    raise
" 2>/dev/null; then
        log_success "Mock display test passed"
    else
        log_error "Mock display test failed"
        return 1
    fi
    
    # Test real hardware display
    log_info "Testing real hardware display..."
    if DISPLAY_TYPE=it8951 python -c "
import sys
sys.path.insert(0, 'src')
from config.settings import Settings
from display.it8951_driver import IT8951Driver
from PIL import Image
try:
    settings = Settings()
    settings.display_type = 'it8951'
    driver = IT8951Driver(settings)
    print(f'Hardware display: {driver.width}x{driver.height}')
    
    # Create a simple white image and test display
    img = Image.new('L', (driver.width, driver.height), 255)
    success = driver.update(img, force_full_refresh=True)
    if success:
        print('Hardware display test passed')
        driver.sleep()
    else:
        raise Exception('Display update failed')
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
        log_info "  - IT8951 library not properly installed"
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
    if DISPLAY_TYPE=it8951 python src/main.py --test; then
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
    
    if test_it8951; then
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
