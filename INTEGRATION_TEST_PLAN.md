# End-to-End Integration Test Plan

## Overview

This plan outlines the steps to introduce a comprehensive end-to-end integration test for the Pi Home Dashboard project. The test will render a static HTML page with dynamic content (current time in seconds), convert it to an image, display it on a virtual e-ink display, and update periodically (every 3 seconds) - all running within the Docker container.

## Goals

1. **Static HTML Rendering**: Create a simple HTML page with dynamic content instead of DAKboard
2. **Image Conversion**: Convert the rendered HTML to an image suitable for e-ink display
3. **Virtual Display**: Use the existing omni-epd mock display for testing
4. **Periodic Updates**: Implement 3-second refresh cycles to test the update mechanism
5. **Docker Integration**: Ensure everything runs seamlessly in the Docker container
6. **Test Validation**: Verify the complete pipeline works end-to-end

## Step-by-Step Implementation Plan

### Phase 1: Create Test HTML Content and Renderer

#### Step 1.1: Create Consolidated Test Module
- **File**: `src/test/integration_test.py`
- **Purpose**: Single file containing all test functionality
- **Features**:
  - Static HTML file generation with embedded JavaScript
  - JavaScript-based dynamic content (timestamp, update counter)
  - Reuse existing Chromium headless browser setup
  - Test validation and monitoring
  - Performance metrics collection
  - Test artifact collection

### Phase 2: Extend Dashboard Renderer for Testing

#### Step 2.1: Add Test Mode to Dashboard Renderer
- **File**: `src/dashboard/renderer.py` (modify existing)
- **Changes**:
  - Add `integration_test` dashboard type alongside `dakboard` and `custom`
  - Implement `_render_integration_test()` method
  - Use existing Chromium setup to render local static HTML file
  - Leverage existing browser configuration and timeout settings
  - Optimize rendering parameters for fast updates

#### Step 2.2: Update Settings for Test Mode
- **File**: `src/config/settings.py` (modify existing)
- **Changes**:
  - Add integration test configuration options
  - 3-second update interval for test mode
  - Test mode flags and local content paths
  - Mock display configuration

### Phase 3: Docker Integration and Command Line Interface

#### Step 3.1: Update Docker Configuration
- **File**: `docker-compose.yml` (modify existing)
- **Changes**:
  - Add integration test service
  - Include test volume mounts for artifacts
  - Add test command options
  - Configure environment for testing

#### Step 3.2: Add Integration Test Commands
- **File**: `src/main.py` (modify existing)
- **Changes**:
  - Add `--integration-test` command line option
  - Add `--test-duration` parameter (default: 60 seconds)
  - Add `--test-interval` parameter (default: 3 seconds)
  - Integration with existing logging and cleanup

#### Step 3.3: Update .gitignore for Test Artifacts
- **File**: `.gitignore` (modify existing)
- **Changes**:
  - Add `test_results/` directory to ignore test artifacts
  - Add temporary test files and screenshots
  - Exclude performance logs and reports from version control

## Detailed Implementation Steps

### Step 1: Create Test Directory Structure

```bash
# Create minimal test directory structure
mkdir -p src/test
mkdir -p test_results/screenshots
mkdir -p test_results/logs
```

### Step 2: Create Consolidated Integration Test Module

**File: `src/test/integration_test.py`**
- Create static HTML file with embedded JavaScript for dynamic content
- Include all test functionality in single module:
  - Static HTML file generation with JavaScript-based dynamic updates
  - Reuse existing Chromium browser setup from dashboard renderer
  - Test validation and performance monitoring
  - Test artifact collection and reporting

### Step 3: Extend Dashboard Renderer

**Modify: `src/dashboard/renderer.py`**
- Add `integration_test` rendering mode
- Reuse existing `_render_dakboard()` method structure for local HTML files
- Use existing Chromium browser configuration and command setup
- Point to local static HTML file instead of external URL
- Optimize for fast refresh cycles with existing browser timeout settings

### Step 4: Update Configuration Settings

**Modify: `src/config/settings.py`**
- Add integration test configuration options
- Include 3-second update interval for test mode
- Add test mode flags and artifact paths

### Step 5: Update Docker Configuration

**Modify: `docker-compose.yml`**
- Add integration test service
- Configure test environment variables
- Set up volume mounts for test artifacts

### Step 6: Add Command Line Interface

**Modify: `src/main.py`**
- Add integration test command options
- Integrate with existing argument parser
- Add test-specific logging and cleanup

### Step 7: Update .gitignore for Test Artifacts

**Modify: `.gitignore`**
- Add test artifact directories and files
- Exclude temporary test files from version control
- Ignore performance logs and screenshots

## Expected Outcomes

### Test Execution Flow
1. **Initialization**: Start Docker container with test configuration
2. **HTML Generation**: Create test HTML with current timestamp
3. **Rendering**: Convert HTML to image using headless browser
4. **Display Update**: Send image to virtual e-ink display
5. **Validation**: Verify update occurred and timestamp changed
6. **Repeat**: Continue cycle every 3 seconds for specified duration
7. **Reporting**: Generate test summary and artifacts

### Success Criteria
- ✅ HTML renders correctly with dynamic content
- ✅ Images are generated and properly formatted for e-ink
- ✅ Virtual display updates successfully
- ✅ Updates occur every 3 seconds consistently
- ✅ Timestamps increment correctly
- ✅ No memory leaks or resource issues
- ✅ All operations complete within Docker container
- ✅ Test artifacts are collected and accessible

### Performance Targets
- **Render Time**: < 2 seconds per update
- **Memory Usage**: < 512MB sustained
- **CPU Usage**: < 50% average
- **Update Accuracy**: 99%+ on-time updates
- **Error Rate**: < 1% failed updates

## Simplified File Structure After Implementation

```
pi-home-dash/
├── src/
│   ├── main.py                     # Modified with test commands
│   ├── dashboard/
│   │   └── renderer.py             # Modified with integration_test mode
│   ├── config/
│   │   └── settings.py             # Modified with test configuration
│   └── test/
│       ├── __init__.py
│       ├── integration_test.py     # Single consolidated test module
│       └── test_dashboard.html     # Static HTML file with JavaScript
├── docker-compose.yml              # Modified with test service
└── test_results/                   # Generated test artifacts
    ├── screenshots/
    ├── logs/
    └── reports/
```

**Key Simplifications:**
- **Single test file**: All test functionality consolidated into `src/test/integration_test.py`
- **Static HTML with JavaScript**: HTML file with embedded JavaScript for dynamic content (no server needed)
- **Reuse existing browser setup**: Leverage existing Chromium configuration from dashboard renderer
- **Integrated settings**: Test configuration added to existing `src/config/settings.py`
- **No separate scripts**: Test execution handled through main.py command line options
- **Minimal directory structure**: Only essential directories created
- **Git-ignored artifacts**: Test results excluded from version control

**Files Modified:**
- `src/main.py` - Add integration test commands
- `src/dashboard/renderer.py` - Add integration_test mode
- `src/config/settings.py` - Add test configuration
- `docker-compose.yml` - Add test service
- `.gitignore` - Exclude test artifacts

## .gitignore Updates

Add the following entries to `.gitignore` to exclude test artifacts from version control:

```gitignore
# Integration test artifacts
test_results/
test_results/screenshots/
test_results/logs/
test_results/reports/

# Temporary test files
temp/test_*.png
temp/integration_test_*
cache/test_*
src/test/test_dashboard.html

# Test performance logs
*.test.log
integration_test_*.csv
test_performance_*.json

# Browser test artifacts
chromium_test_*
screenshot_*.png
test_display_update_*.png
```

## Docker Commands for Testing

```bash
# Build test environment
docker-compose build

# Run integration test (60 seconds, 3-second intervals)
docker-compose run --rm pi-home-dash python src/main.py --integration-test --test-duration 60

# Run integration test with custom parameters
docker-compose run --rm pi-home-dash python src/main.py --integration-test --test-duration 180 --test-interval 5

# Run test with monitoring
docker-compose up pi-home-dash-test

# View test logs
docker-compose logs -f pi-home-dash-test

# Collect test artifacts (handled automatically during test execution)
docker-compose run --rm pi-home-dash python src/main.py --integration-test --collect-artifacts
```

## Monitoring and Debugging

### Real-time Monitoring
- Live update counter display
- Performance metrics (render time, memory usage)
- Error rate tracking
- Screenshot preview (if display available)

### Debug Information
- Detailed timing logs
- Image processing statistics
- Browser console output
- Display driver status

### Test Artifacts
- Timestamped screenshots
- Performance data CSV
- Error logs with stack traces
- Test summary report

## Next Steps After Implementation

1. **Validation**: Run initial tests to verify basic functionality
2. **Optimization**: Tune performance based on test results
3. **Documentation**: Create user guide for running integration tests
4. **CI/CD Integration**: Add tests to automated build pipeline
5. **Extended Testing**: Add more complex test scenarios
6. **Hardware Testing**: Validate with actual e-ink display hardware

This comprehensive plan provides a structured approach to implementing end-to-end integration testing for the Pi Home Dashboard project, ensuring all components work together seamlessly in a containerized environment.
