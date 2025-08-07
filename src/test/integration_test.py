"""
Integration test module for Pi Home Dashboard.
Tests the complete pipeline: HTML rendering -> Image conversion -> Virtual e-ink display.
"""

import logging
import time
import os
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import tempfile
import shutil

# Import project modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import Settings
from dashboard.renderer import DashboardRenderer
from display.eink_driver import EInkDriver


class IntegrationTestRunner:
    """Main integration test runner class."""
    
    def __init__(self, test_duration: int = 60, test_interval: int = 3):
        """
        Initialize the integration test runner.
        
        Args:
            test_duration: Total test duration in seconds
            test_interval: Interval between updates in seconds
        """
        self.test_duration = test_duration
        self.test_interval = test_interval
        
        # Setup test settings
        self.settings = self._create_test_settings()
        
        # Initialize components
        self.renderer = DashboardRenderer(self.settings)
        self.display = EInkDriver(self.settings)
        
        # Test state
        self.start_time: Optional[float] = None
        self.update_count = 0
        self.test_results = []
        self.performance_metrics = []
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Test artifacts paths
        self.test_results_dir = Path("test_results")
        self.screenshots_dir = self.test_results_dir / "screenshots"
        self.logs_dir = self.test_results_dir / "logs"
        self.reports_dir = self.test_results_dir / "reports"
        
        # Ensure directories exist
        for dir_path in [self.screenshots_dir, self.logs_dir, self.reports_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def _create_test_settings(self) -> Settings:
        """Create test-specific settings."""
        settings = Settings()
        
        # Override for integration test
        settings.dashboard_type = "integration_test"
        settings.update_interval = self.test_interval
        settings.debug_mode = True
        
        # Test-specific paths
        settings.test_html_path = Path(__file__).parent / "test_dashboard.html"
        
        # Ensure mock display for testing
        settings.epd_device = "omni_epd.mock"
        
        return settings
    
    def run_test(self) -> Dict:
        """
        Run the complete integration test.
        
        Returns:
            Dict containing test results and metrics
        """
        self.logger.info(f"Starting integration test - Duration: {self.test_duration}s, Interval: {self.test_interval}s")
        
        try:
            # Initialize test
            self._initialize_test()
            
            # Run test loop
            self._run_test_loop()
            
            # Generate final report
            results = self._generate_final_report()
            
            self.logger.info("Integration test completed successfully")
            return results
            
        except Exception as e:
            self.logger.error(f"Integration test failed: {e}")
            return {"success": False, "error": str(e)}
        
        finally:
            self._cleanup_test()
    
    def _initialize_test(self):
        """Initialize the test environment."""
        self.start_time = time.time()
        self.update_count = 0
        self.test_results = []
        self.performance_metrics = []
        
        self.logger.info("Test environment initialized")
        
        # Verify test HTML file exists
        if self.settings.test_html_path is None or not self.settings.test_html_path.exists():
            raise FileNotFoundError(f"Test HTML file not found: {self.settings.test_html_path}")
        
        # Test initial rendering
        self.logger.info("Testing initial rendering...")
        test_image = self.renderer.render()
        if test_image is None:
            raise RuntimeError("Initial rendering test failed")
        
        self.logger.info("Initial rendering test passed")
    
    def _run_test_loop(self):
        """Run the main test loop with periodic updates."""
        self.logger.info("Starting test loop...")
        
        while True:
            current_time = time.time()
            elapsed_time = current_time - (self.start_time or 0)
            
            # Check if test duration exceeded
            if elapsed_time >= self.test_duration:
                self.logger.info(f"Test duration ({self.test_duration}s) reached")
                break
            
            # Perform update cycle
            cycle_start = time.time()
            success = self._perform_update_cycle()
            cycle_duration = time.time() - cycle_start
            
            # Record results
            self._record_cycle_results(success, cycle_duration, elapsed_time)
            
            # Wait for next interval
            sleep_time = max(0, self.test_interval - cycle_duration)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def _perform_update_cycle(self) -> bool:
        """
        Perform a single update cycle.
        
        Returns:
            bool: True if cycle completed successfully
        """
        try:
            self.update_count += 1
            self.logger.info(f"Update cycle {self.update_count} starting...")
            
            # Render dashboard
            render_start = time.time()
            dashboard_image = self.renderer.render()
            render_duration = time.time() - render_start
            
            if dashboard_image is None:
                self.logger.error(f"Rendering failed in cycle {self.update_count}")
                return False
            
            # Update display
            display_start = time.time()
            display_success = self.display.update(dashboard_image, force_full_refresh=False)
            display_duration = time.time() - display_start
            
            if not display_success:
                self.logger.error(f"Display update failed in cycle {self.update_count}")
                return False
            
            # Save screenshot for validation
            self._save_screenshot(dashboard_image)
            
            # Record performance metrics
            self.performance_metrics.append({
                'cycle': self.update_count,
                'render_time': render_duration,
                'display_time': display_duration,
                'total_time': render_duration + display_duration,
                'timestamp': time.time()
            })
            
            self.logger.info(f"Update cycle {self.update_count} completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in update cycle {self.update_count}: {e}")
            return False
    
    def _record_cycle_results(self, success: bool, cycle_duration: float, elapsed_time: float):
        """Record the results of a test cycle."""
        result = {
            'cycle': self.update_count,
            'success': success,
            'cycle_duration': cycle_duration,
            'elapsed_time': elapsed_time,
            'timestamp': datetime.now().isoformat()
        }
        
        self.test_results.append(result)
        
        # Log progress
        progress = (elapsed_time / self.test_duration) * 100
        self.logger.info(f"Progress: {progress:.1f}% - Cycle {self.update_count} - {'SUCCESS' if success else 'FAILED'}")
    
    def _save_screenshot(self, image):
        """Save screenshot for validation."""
        try:
            timestamp = int(time.time())
            filename = f"test_screenshot_{self.update_count:04d}_{timestamp}.png"
            filepath = self.screenshots_dir / filename
            
            image.save(filepath)
            self.logger.debug(f"Screenshot saved: {filepath}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save screenshot: {e}")
    
    def _generate_final_report(self) -> Dict:
        """Generate final test report with all metrics."""
        end_time = time.time()
        total_duration = end_time - (self.start_time or 0)
        
        # Calculate statistics
        successful_cycles = sum(1 for r in self.test_results if r['success'])
        failed_cycles = len(self.test_results) - successful_cycles
        success_rate = (successful_cycles / len(self.test_results)) * 100 if self.test_results else 0
        
        # Performance statistics
        if self.performance_metrics:
            render_times = [m['render_time'] for m in self.performance_metrics]
            display_times = [m['display_time'] for m in self.performance_metrics]
            total_times = [m['total_time'] for m in self.performance_metrics]
            
            perf_stats = {
                'avg_render_time': sum(render_times) / len(render_times),
                'max_render_time': max(render_times),
                'min_render_time': min(render_times),
                'avg_display_time': sum(display_times) / len(display_times),
                'max_display_time': max(display_times),
                'min_display_time': min(display_times),
                'avg_total_time': sum(total_times) / len(total_times),
                'max_total_time': max(total_times),
                'min_total_time': min(total_times)
            }
        else:
            perf_stats = {}
        
        # Create final report
        report = {
            'success': True,
            'test_config': {
                'duration': self.test_duration,
                'interval': self.test_interval,
                'total_cycles': len(self.test_results)
            },
            'results': {
                'successful_cycles': successful_cycles,
                'failed_cycles': failed_cycles,
                'success_rate': success_rate,
                'total_duration': total_duration
            },
            'performance': perf_stats,
            'artifacts': {
                'screenshots': len(list(self.screenshots_dir.glob("*.png"))),
                'logs_dir': str(self.logs_dir),
                'reports_dir': str(self.reports_dir)
            }
        }
        
        # Save detailed reports
        self._save_detailed_reports(report)
        
        return report
    
    def _save_detailed_reports(self, summary_report: Dict):
        """Save detailed test reports to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save summary report
        summary_file = self.reports_dir / f"test_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary_report, f, indent=2)
        
        # Save detailed results
        results_file = self.reports_dir / f"test_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        # Save performance metrics as CSV
        if self.performance_metrics:
            perf_file = self.reports_dir / f"performance_metrics_{timestamp}.csv"
            with open(perf_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.performance_metrics[0].keys())
                writer.writeheader()
                writer.writerows(self.performance_metrics)
        
        self.logger.info(f"Detailed reports saved to {self.reports_dir}")
    
    def _cleanup_test(self):
        """Clean up test resources."""
        try:
            if hasattr(self, 'display') and self.display:
                self.display.cleanup()
            
            self.logger.info("Test cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


class TestValidator:
    """Validates test results and generates validation reports."""
    
    def __init__(self, test_results_dir: Path):
        self.test_results_dir = test_results_dir
        self.logger = logging.getLogger(__name__)
    
    def validate_test_run(self, report: Dict) -> Dict:
        """
        Validate a test run against success criteria.
        
        Args:
            report: Test report dictionary
            
        Returns:
            Dict containing validation results
        """
        validation_results = {
            'overall_pass': True,
            'criteria_results': {},
            'recommendations': []
        }
        
        # Success rate validation (target: >95%)
        success_rate = report['results']['success_rate']
        validation_results['criteria_results']['success_rate'] = {
            'value': success_rate,
            'target': 95.0,
            'pass': success_rate >= 95.0
        }
        
        if success_rate < 95.0:
            validation_results['overall_pass'] = False
            validation_results['recommendations'].append(
                f"Success rate ({success_rate:.1f}%) below target (95%). Check for rendering or display issues."
            )
        
        # Performance validation (target: <2s per update)
        if 'performance' in report and 'avg_total_time' in report['performance']:
            avg_time = report['performance']['avg_total_time']
            validation_results['criteria_results']['performance'] = {
                'value': avg_time,
                'target': 2.0,
                'pass': avg_time < 2.0
            }
            
            if avg_time >= 2.0:
                validation_results['overall_pass'] = False
                validation_results['recommendations'].append(
                    f"Average update time ({avg_time:.2f}s) exceeds target (2.0s). Consider optimization."
                )
        
        # Screenshot validation
        screenshots = list(self.test_results_dir.glob("screenshots/*.png"))
        expected_screenshots = report['test_config']['total_cycles']
        screenshot_ratio = len(screenshots) / expected_screenshots if expected_screenshots > 0 else 0
        
        validation_results['criteria_results']['screenshots'] = {
            'value': len(screenshots),
            'expected': expected_screenshots,
            'ratio': screenshot_ratio,
            'pass': screenshot_ratio >= 0.9
        }
        
        if screenshot_ratio < 0.9:
            validation_results['overall_pass'] = False
            validation_results['recommendations'].append(
                f"Screenshot capture rate ({screenshot_ratio:.1%}) below 90%. Check screenshot saving functionality."
            )
        
        return validation_results


def run_integration_test(duration: int = 60, interval: int = 3, collect_artifacts: bool = True) -> Dict:
    """
    Main entry point for running integration tests.
    
    Args:
        duration: Test duration in seconds
        interval: Update interval in seconds
        collect_artifacts: Whether to collect and validate test artifacts
        
    Returns:
        Dict containing test results
    """
    # Setup logging for test
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('test_results/logs/integration_test.log')
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("STARTING PI HOME DASHBOARD INTEGRATION TEST")
    logger.info("=" * 60)
    
    try:
        # Run the test
        test_runner = IntegrationTestRunner(duration, interval)
        results = test_runner.run_test()
        
        # Validate results if requested
        if collect_artifacts and results.get('success', False):
            validator = TestValidator(Path("test_results"))
            validation = validator.validate_test_run(results)
            results['validation'] = validation
            
            logger.info("=" * 60)
            logger.info("TEST VALIDATION RESULTS")
            logger.info("=" * 60)
            logger.info(f"Overall Pass: {'✅ PASS' if validation['overall_pass'] else '❌ FAIL'}")
            
            for criterion, result in validation['criteria_results'].items():
                status = '✅ PASS' if result['pass'] else '❌ FAIL'
                logger.info(f"{criterion}: {status}")
            
            if validation['recommendations']:
                logger.info("\nRecommendations:")
                for rec in validation['recommendations']:
                    logger.info(f"- {rec}")
        
        logger.info("=" * 60)
        logger.info("INTEGRATION TEST COMPLETED")
        logger.info("=" * 60)
        
        return results
        
    except Exception as e:
        logger.error(f"Integration test failed with error: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # Allow running the test directly
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Pi Home Dashboard Integration Test')
    parser.add_argument('--duration', type=int, default=60, help='Test duration in seconds')
    parser.add_argument('--interval', type=int, default=3, help='Update interval in seconds')
    parser.add_argument('--no-artifacts', action='store_true', help='Skip artifact collection')
    
    args = parser.parse_args()
    
    results = run_integration_test(
        duration=args.duration,
        interval=args.interval,
        collect_artifacts=not args.no_artifacts
    )
    
    # Exit with appropriate code
    exit_code = 0 if results.get('success', False) else 1
    exit(exit_code)
