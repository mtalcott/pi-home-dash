#!/bin/bash

# Common Setup Functions
# Shared setup logic between Dockerfile and Pi setup script
# This keeps the setup DRY between different environments

# Common system dependencies (core packages needed by both environments)
get_common_system_deps() {
    echo "git gcc python3-dev build-essential fonts-dejavu-core"
}

# Docker-specific system dependencies
get_docker_system_deps() {
    echo "chromium xvfb"
}

# Pi-specific system dependencies
get_pi_system_deps() {
    echo "chromium python3-pip python3-venv python3-spidev python3-rpi.gpio"
}

# Install common system dependencies
install_common_system_deps() {
    local extra_deps="${1:-}"
    local all_deps="$(get_common_system_deps) $extra_deps"
    
    echo "Installing system dependencies: $all_deps"
    apt-get update
    apt-get install -y $all_deps
    apt-get clean
    rm -rf /var/lib/apt/lists/*
}

# Install Docker-specific system dependencies
install_docker_system_deps() {
    install_common_system_deps "$(get_docker_system_deps)"
}

# Install Pi-specific system dependencies (requires sudo)
install_pi_system_deps() {
    local all_deps="$(get_common_system_deps) $(get_pi_system_deps)"
    
    echo "Installing system dependencies: $all_deps"
    sudo apt-get update
    sudo apt-get install -y $all_deps
    sudo apt-get clean
    sudo rm -rf /var/lib/apt/lists/*
}

# Common Python setup steps
setup_python_common() {
    local requirements_file="${1:-requirements.txt}"
    
    if [[ -f "$requirements_file" ]]; then
        echo "Installing Python dependencies from $requirements_file"
        pip install --no-cache-dir -r "$requirements_file"
        return 0
    else
        echo "Error: $requirements_file not found"
        return 1
    fi
}

# Common directory structure
create_common_directories() {
    local base_dir="${1:-/app}"
    
    local dirs=(
        "$base_dir/cache"
        "$base_dir/temp" 
        "$base_dir/logs"
        "$base_dir/test_results"
        "$base_dir/test_results/screenshots"
        "$base_dir/test_results/reports"
        "$base_dir/test_results/logs"
    )
    
    echo "Creating directories: ${dirs[*]}"
    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
    done
}

# Common environment variables for Docker
get_docker_env_vars() {
    cat << EOF
PYTHONPATH=/app/src
DISPLAY=:99
DEBUG=false
UPDATE_INTERVAL=60
EOF
}

# Common environment variables for Pi
get_pi_env_vars() {
    local home_dir="${1:-$HOME}"
    cat << EOF
PYTHONPATH=$home_dir/pi-home-dash/src
DISPLAY=:0
DEBUG=false
UPDATE_INTERVAL=60
DAKBOARD_URL=https://dakboard.com/screen/your-screen-id
EOF
}

# Common test command
run_common_test() {
    local python_cmd="${1:-python}"
    local src_dir="${2:-src}"
    
    echo "Running test: $python_cmd $src_dir/main.py --test"
    "$python_cmd" "$src_dir/main.py" --test
}

# Validate common requirements
validate_common_setup() {
    local python_cmd="${1:-python}"
    
    echo "Validating setup with $python_cmd"
    
    # Check if Python is available
    if ! command -v "$python_cmd" &> /dev/null; then
        echo "Error: $python_cmd not found"
        return 1
    fi
    
    # Check if required Python packages are installed
    local required_packages=(
        "pillow"
    )
    
    for package in "${required_packages[@]}"; do
        if ! "$python_cmd" -c "import $package" 2>/dev/null; then
            echo "Error: Python package '$package' not found"
            return 1
        fi
    done
    
    # Check omni-epd separately as it might not be available in all environments
    if ! "$python_cmd" -c "import omni_epd" 2>/dev/null; then
        echo "Warning: omni-epd package not found (may be expected in some environments)"
    fi
    
    return 0
}

# Execute function if called directly (allows RUN commands in Dockerfile)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Called directly, execute the function passed as argument
    "$@"
fi
