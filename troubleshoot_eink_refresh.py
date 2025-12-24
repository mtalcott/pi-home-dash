#!/usr/bin/env python3
"""
E-ink Display Refresh Troubleshooting Utility

A comprehensive utility for troubleshooting failed full refreshes on IT8951-based e-ink displays.
Includes advanced testing with different refresh modes, VCOM settings, screenshot-based testing,
and diagnostic recovery procedures.
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any, Union
from PIL import Image, ImageDraw, ImageFont

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.settings import Settings
from display.it8951_driver import IT8951Driver

try:
    from IT8951.display import AutoEPDDisplay
    from IT8951 import constants
    IT8951_AVAILABLE = True
except ImportError:
    IT8951_AVAILABLE = False
    # Create dummy types for type checking when library not available
    AutoEPDDisplay = type(None)  # type: ignore
    constants = type(None)()  # type: ignore


class EInkRefreshTroubleshooter:
    """Advanced troubleshooting utility for e-ink display refresh issues."""
    
    def __init__(self, verbose: bool = False, interactive: bool = True):
        """Initialize the troubleshooting utility."""
        # Setup logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('troubleshoot_eink.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.interactive = interactive
        
        # Load settings
        self.settings = Settings()
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            self.settings.load_from_file(env_file)
            self.logger.info(f"Loaded configuration from {env_file}")
        
        # Initialize driver
        self.driver = IT8951Driver(self.settings)
        self.direct_display = None
        
        # Test results tracking
        self.test_results = {}
        self.failed_modes = []
        self.successful_modes = []
        
        # VCOM test values (typical range for IT8951)
        self.vcom_test_values = [-1.0, -1.2, -1.4, -1.46, -1.5, -1.6, -1.8, -2.0]
        
        # IT8951 display modes to test
        self.display_modes = {
            'INIT': 'Full refresh with highest quality (slowest)',
            'DU': 'Direct update (fastest, partial refresh)',
            'GC16': 'Grayscale 16 levels (full refresh)',
            'GL16': 'Grayscale 16 levels (fast)',
            'GLR16': 'Grayscale 16 levels with reduced flicker',
            'GLD16': 'Grayscale 16 levels with dithering',
            'A2': 'Animation mode (2 levels, very fast)',
            'DU4': '4-level direct update'
        }
        
        # Screenshot test directory
        self.screenshot_dir = Path(__file__).parent / "screenshots"
        
        # Initialize direct IT8951 access if available
        self._init_direct_access()
    
    def manual_verification(self, test_name: str, expected_content: str = "") -> bool:
        """Prompt user for manual verification of display rendering."""
        print(f"\n🔍 Manual Verification Required for: {test_name}")
        if expected_content:
            print(f"Expected content: {expected_content}")
        
        print("\nPlease examine the e-ink display and verify:")
        print("1. Text is clearly readable and properly positioned")
        print("2. No ghosting or artifacts from previous images")
        print("3. Borders and graphics are crisp and complete")
        print("4. No flickering or incomplete refresh areas")
        print("5. Overall image quality is acceptable")
        
        while True:
            try:
                response = input("\nDoes the display look correct? (y/n): ").lower().strip()
                if response in ['y', 'yes']:
                    print("✅ User confirmed display rendering is correct")
                    return True
                elif response in ['n', 'no']:
                    print("❌ User reported display rendering issues")
                    return False
                else:
                    print("Please enter 'y' for yes or 'n' for no")
            except (KeyboardInterrupt, EOFError):
                print("\n⚠️ Manual verification interrupted - assuming failure")
                return False
    
    def _init_direct_access(self):
        """Initialize direct IT8951 access for advanced testing."""
        if not IT8951_AVAILABLE or self.driver.mock_mode:
            self.logger.warning("Direct IT8951 access not available")
            return
        
        try:
            self.direct_display = AutoEPDDisplay(
                vcom=self.settings.it8951_vcom,
                rotate=self.settings.it8951_rotate,
                spi_hz=self.settings.it8951_spi_hz,
                mirror=self.settings.it8951_mirror
            )
            if self.direct_display:
                self.logger.info("Direct IT8951 access initialized successfully")
                self.logger.info(f"Display: {self.direct_display.width}x{self.direct_display.height}")
                self.logger.info(f"Current VCOM: {self.direct_display.epd.get_vcom()}")
            else:
                self.logger.error("Failed to initialize direct IT8951 access")
        except Exception as e:
            self.logger.error(f"Error initializing direct IT8951 access: {e}")
            self.direct_display = None
    
    def create_diagnostic_image(self, test_name: str, details: str = "") -> Image.Image:
        """Create a diagnostic test image with test information."""
        # Create white background
        image = Image.new('L', (self.settings.display_width, self.settings.display_height), 255)
        draw = ImageDraw.Draw(image)
        
        # Load fonts
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
            detail_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except (OSError, IOError):
            title_font = ImageFont.load_default()
            detail_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Draw header
        draw.text((20, 20), "E-ink Diagnostic Test", fill=0, font=title_font)
        
        # Draw test name
        draw.text((20, 80), f"Test: {test_name}", fill=0, font=detail_font)
        
        # Draw details if provided
        if details:
            y_pos = 120
            for line in details.split('\n'):
                if line.strip():
                    draw.text((20, y_pos), line.strip(), fill=0, font=detail_font)
                    y_pos += 30
        
        # Add timestamp
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        draw.text((20, self.settings.display_height - 40), f"Time: {timestamp}", fill=0, font=small_font)
        
        # Add VCOM info
        vcom_text = f"VCOM: {self.settings.it8951_vcom}V"
        draw.text((20, self.settings.display_height - 60), vcom_text, fill=0, font=small_font)
        
        # Add border
        draw.rectangle([10, 10, self.settings.display_width-10, self.settings.display_height-10], 
                      outline=0, width=2)
        
        return image
    
    def test_display_mode(self, mode_name: str, description: str) -> bool:
        """Test a specific IT8951 display mode."""
        if not self.direct_display:
            self.logger.warning(f"Cannot test {mode_name} - direct display not available")
            return False
        
        self.logger.info(f"Testing display mode: {mode_name} ({description})")
        
        try:
            # Create test image
            test_details = f"Mode: {mode_name}\n{description}"
            image = self.create_diagnostic_image(f"Mode Test: {mode_name}", test_details)
            processed_image = self.driver._process_image(image)
            
            # Get the display mode constant
            if not hasattr(constants.DisplayModes, mode_name):
                self.logger.error(f"Unknown display mode: {mode_name}")
                return False
            
            mode = getattr(constants.DisplayModes, mode_name)
            
            # Perform the test
            start_time = time.time()
            self.direct_display.frame_buf.paste(processed_image, (0, 0))
            
            if mode_name in ['INIT', 'GC16']:
                # Full refresh modes
                self.direct_display.draw_full(mode)
            else:
                # Partial refresh modes
                self.direct_display.draw_partial(mode)
            
            duration = time.time() - start_time
            
            self.logger.info(f"✅ Mode {mode_name} completed in {duration:.2f}s")
            self.successful_modes.append(mode_name)
            self.test_results[f"mode_{mode_name.lower()}"] = {
                'success': True,
                'duration': duration,
                'description': description
            }
            
            # Wait for display to settle
            time.sleep(1)
            
            # Manual verification of display rendering
            manual_result = self.manual_verification(
                f"Display Mode: {mode_name}", 
                f"Expected: Diagnostic test screen with mode information and {description}"
            )
            
            if not manual_result:
                self.test_results[f"mode_{mode_name.lower()}"]["manual_verification"] = False
                self.logger.warning(f"Manual verification failed for mode {mode_name}")
            else:
                self.test_results[f"mode_{mode_name.lower()}"]["manual_verification"] = True
            
            return manual_result
            
        except Exception as e:
            self.logger.error(f"❌ Mode {mode_name} failed: {e}")
            self.failed_modes.append(mode_name)
            self.test_results[f"mode_{mode_name.lower()}"] = {
                'success': False,
                'error': str(e),
                'description': description,
                'manual_verification': False
            }
            return False
    
    def test_vcom_setting(self, vcom_value: float) -> bool:
        """Test a specific VCOM setting."""
        if not self.direct_display:
            self.logger.warning(f"Cannot test VCOM {vcom_value} - direct display not available")
            return False
        
        self.logger.info(f"Testing VCOM setting: {vcom_value}V")
        
        try:
            # Set VCOM
            self.direct_display.epd.set_vcom(vcom_value)
            actual_vcom = self.direct_display.epd.get_vcom()
            
            # Create test image
            test_details = f"VCOM: {vcom_value}V\nActual: {actual_vcom}V"
            image = self.create_diagnostic_image(f"VCOM Test: {vcom_value}V", test_details)
            processed_image = self.driver._process_image(image)
            
            # Test with full refresh (INIT mode)
            start_time = time.time()
            self.direct_display.frame_buf.paste(processed_image, (0, 0))
            self.direct_display.draw_full(constants.DisplayModes.INIT)
            duration = time.time() - start_time
            
            self.logger.info(f"✅ VCOM {vcom_value}V test completed in {duration:.2f}s (actual: {actual_vcom}V)")
            self.test_results[f"vcom_{str(vcom_value).replace('-', 'neg').replace('.', '_')}"] = {
                'success': True,
                'requested_vcom': vcom_value,
                'actual_vcom': actual_vcom,
                'duration': duration
            }
            
            # Wait for display to settle
            time.sleep(2)
            return True
            
        except Exception as e:
            self.logger.error(f"❌ VCOM {vcom_value}V test failed: {e}")
            self.test_results[f"vcom_{str(vcom_value).replace('-', 'neg').replace('.', '_')}"] = {
                'success': False,
                'requested_vcom': vcom_value,
                'error': str(e)
            }
            return False
    
    def test_screenshot_rendering(self, screenshot_path: Path) -> bool:
        """Test rendering an existing screenshot to the display."""
        if not screenshot_path.exists():
            self.logger.error(f"Screenshot not found: {screenshot_path}")
            return False
        
        self.logger.info(f"Testing screenshot rendering: {screenshot_path.name}")
        
        try:
            # Load and process screenshot
            screenshot = Image.open(screenshot_path)
            
            # Resize to display dimensions if needed
            if screenshot.size != (self.settings.display_width, self.settings.display_height):
                screenshot = screenshot.resize(
                    (self.settings.display_width, self.settings.display_height),
                    Image.Resampling.LANCZOS
                )
            
            # Convert to grayscale for e-ink
            if screenshot.mode != 'L':
                screenshot = screenshot.convert('L')
            
            # Test with different refresh methods
            results = {}
            
            # Test 1: Driver update with full refresh
            self.logger.info("  Testing driver full refresh...")
            start_time = time.time()
            success1 = self.driver.update(screenshot, force_full_refresh=True)
            duration1 = time.time() - start_time
            results['driver_full'] = {'success': success1, 'duration': duration1}
            
            time.sleep(2)
            
            # Test 2: Driver update with partial refresh
            self.logger.info("  Testing driver partial refresh...")
            start_time = time.time()
            success2 = self.driver.update(screenshot, force_full_refresh=False)
            duration2 = time.time() - start_time
            results['driver_partial'] = {'success': success2, 'duration': duration2}
            
            time.sleep(2)
            
            # Test 3: Direct INIT mode (if available)
            if self.direct_display:
                self.logger.info("  Testing direct INIT mode...")
                start_time = time.time()
                try:
                    self.direct_display.frame_buf.paste(screenshot, (0, 0))
                    self.direct_display.draw_full(constants.DisplayModes.INIT)
                    duration3 = time.time() - start_time
                    results['direct_init'] = {'success': True, 'duration': duration3}
                except Exception as e:
                    results['direct_init'] = {'success': False, 'error': str(e)}
            
            # Log results
            all_success = all(r.get('success', False) for r in results.values())
            self.logger.info(f"Screenshot test results: {results}")
            
            self.test_results[f"screenshot_{screenshot_path.stem}"] = {
                'success': all_success,
                'file': str(screenshot_path),
                'methods': results
            }
            
            return all_success
            
        except Exception as e:
            self.logger.error(f"❌ Screenshot rendering failed: {e}")
            self.test_results[f"screenshot_{screenshot_path.stem}"] = {
                'success': False,
                'file': str(screenshot_path),
                'error': str(e)
            }
            return False
    
    def run_hardware_diagnostics(self) -> Dict[str, Any]:
        """Run comprehensive hardware diagnostics."""
        self.logger.info("Running hardware diagnostics...")
        
        diagnostics = {
            'it8951_available': IT8951_AVAILABLE,
            'driver_mock_mode': self.driver.mock_mode,
            'hardware_initialized': self.driver.hardware_initialized,
            'direct_access': self.direct_display is not None,
        }
        
        if self.direct_display:
            try:
                # Get hardware info
                diagnostics.update({
                    'display_width': self.direct_display.width,
                    'display_height': self.direct_display.height,
                    'current_vcom': self.direct_display.epd.get_vcom(),
                    'device_info': 'Available' if hasattr(self.direct_display.epd, 'dev_info') else 'Not available'
                })
                
                # Test basic communication
                try:
                    # Try to read VCOM (tests SPI communication)
                    vcom = self.direct_display.epd.get_vcom()
                    diagnostics['spi_communication'] = True
                    diagnostics['vcom_read'] = vcom
                except Exception as e:
                    diagnostics['spi_communication'] = False
                    diagnostics['spi_error'] = str(e)
                
            except Exception as e:
                diagnostics['hardware_error'] = str(e)
        
        # Test settings
        diagnostics['settings'] = {
            'display_width': self.settings.display_width,
            'display_height': self.settings.display_height,
            'it8951_vcom': self.settings.it8951_vcom,
            'it8951_spi_hz': self.settings.it8951_spi_hz,
            'it8951_mirror': self.settings.it8951_mirror,
            'it8951_rotate': self.settings.it8951_rotate,
            'display_type': self.settings.display_type
        }
        
        self.logger.info(f"Hardware diagnostics completed: {diagnostics}")
        return diagnostics
    
    def recover_from_failed_refresh(self) -> bool:
        """Attempt to recover from a failed refresh state."""
        self.logger.info("Attempting display recovery...")
        
        recovery_steps = [
            ("Clear display buffer", self._recovery_clear_buffer),
            ("Reset with white screen", self._recovery_white_screen),
            ("Test basic communication", self._recovery_test_communication),
            ("Reinitialize display", self._recovery_reinit_display),
            ("Test simple pattern", self._recovery_test_pattern)
        ]
        
        for step_name, step_func in recovery_steps:
            self.logger.info(f"Recovery step: {step_name}")
            try:
                if step_func():
                    self.logger.info(f"✅ {step_name} successful")
                else:
                    self.logger.warning(f"⚠️  {step_name} failed, continuing...")
            except Exception as e:
                self.logger.error(f"❌ {step_name} error: {e}")
        
        # Final test
        return self._recovery_final_test()
    
    def _recovery_clear_buffer(self) -> bool:
        """Clear the display buffer."""
        if not self.direct_display:
            return self.driver.clear_display()
        
        try:
            # Clear the frame buffer
            white_image = Image.new('L', (self.settings.display_width, self.settings.display_height), 255)
            self.direct_display.frame_buf.paste(white_image, (0, 0))
            return True
        except Exception:
            return False
    
    def _recovery_white_screen(self) -> bool:
        """Display a white screen with INIT mode."""
        try:
            white_image = Image.new('L', (self.settings.display_width, self.settings.display_height), 255)
            
            if self.direct_display:
                self.direct_display.frame_buf.paste(white_image, (0, 0))
                self.direct_display.draw_full(constants.DisplayModes.INIT)
            else:
                self.driver.update(white_image, force_full_refresh=True)
            
            time.sleep(2)
            return True
        except Exception:
            return False
    
    def _recovery_test_communication(self) -> bool:
        """Test basic SPI communication."""
        if not self.direct_display:
            return True  # Can't test, assume OK
        
        try:
            # Test VCOM read/write
            original_vcom = self.direct_display.epd.get_vcom()
            test_vcom = -1.5  # Safe test value
            self.direct_display.epd.set_vcom(test_vcom)
            read_vcom = self.direct_display.epd.get_vcom()
            self.direct_display.epd.set_vcom(original_vcom)  # Restore
            
            return abs(read_vcom - test_vcom) < 0.1  # Should be close
        except Exception:
            return False
    
    def _recovery_reinit_display(self) -> bool:
        """Reinitialize the display."""
        try:
            if self.direct_display:
                # Close current connection
                if hasattr(self.direct_display, 'close'):
                    self.direct_display.close()
                
                # Reinitialize
                self.direct_display = AutoEPDDisplay(
                    vcom=self.settings.it8951_vcom,
                    rotate=self.settings.it8951_rotate,
                    spi_hz=self.settings.it8951_spi_hz,
                    mirror=self.settings.it8951_mirror
                )
            
            # Reinitialize driver
            self.driver._init_display()
            return self.driver.hardware_initialized
        except Exception:
            return False
    
    def _recovery_test_pattern(self) -> bool:
        """Test with a simple pattern."""
        try:
            # Create simple test pattern
            image = Image.new('L', (self.settings.display_width, self.settings.display_height), 255)
            draw = ImageDraw.Draw(image)
            
            # Simple black border
            draw.rectangle([10, 10, self.settings.display_width-10, self.settings.display_height-10], 
                          outline=0, width=5)
            
            # Center text
            draw.text((self.settings.display_width//2 - 50, self.settings.display_height//2 - 10), 
                     "RECOVERY TEST", fill=0)
            
            return self.driver.update(image, force_full_refresh=True)
        except Exception:
            return False
    
    def _recovery_final_test(self) -> bool:
        """Final recovery validation test."""
        try:
            # Test both full and partial refresh
            test_image = self.create_diagnostic_image("Recovery Complete", "Display functional")
            
            # Full refresh test
            if not self.driver.update(test_image, force_full_refresh=True):
                return False
            
            time.sleep(1)
            
            # Partial refresh test
            return self.driver.update(test_image, force_full_refresh=False)
        except Exception:
            return False
    
    def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive troubleshooting tests."""
        self.logger.info("Starting comprehensive e-ink refresh troubleshooting...")
        
        # Hardware diagnostics
        self.logger.info("\n=== Hardware Diagnostics ===")
        hardware_diag = self.run_hardware_diagnostics()
        
        # Test all display modes
        self.logger.info("\n=== Display Mode Tests ===")
        for mode_name, description in self.display_modes.items():
            self.test_display_mode(mode_name, description)
            time.sleep(1)  # Brief pause between tests
        
        # Test VCOM values
        self.logger.info("\n=== VCOM Tests ===")
        original_vcom = self.settings.it8951_vcom
        for vcom in self.vcom_test_values:
            self.test_vcom_setting(vcom)
            time.sleep(1)
        
        # Restore original VCOM
        if self.direct_display:
            try:
                self.direct_display.epd.set_vcom(original_vcom)
                self.logger.info(f"Restored VCOM to original value: {original_vcom}V")
            except Exception as e:
                self.logger.warning(f"Failed to restore VCOM: {e}")
        
        # Test screenshots
        self.logger.info("\n=== Screenshot Rendering Tests ===")
        screenshot_files = list(self.screenshot_dir.glob("*.png"))[:3]  # Test up to 3 screenshots
        for screenshot_path in screenshot_files:
            self.test_screenshot_rendering(screenshot_path)
            time.sleep(1)
        
        # Recovery test
        self.logger.info("\n=== Recovery Test ===")
        recovery_success = self.recover_from_failed_refresh()
        self.test_results['recovery'] = {'success': recovery_success}
        
        # Compile results
        results = {
            'hardware_diagnostics': hardware_diag,
            'successful_modes': self.successful_modes,
            'failed_modes': self.failed_modes,
            'test_results': self.test_results,
            'recovery_success': recovery_success,
            'total_tests': len(self.test_results),
            'successful_tests': sum(1 for r in self.test_results.values() if r.get('success', False)),
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return results
    
    def save_results(self, results: Dict[str, Any], output_file: Optional[Path] = None) -> Path:
        """Save test results to a file."""
        if output_file is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = Path(f"eink_troubleshoot_results_{timestamp}.json")
        
        import json
        with output_file.open('w') as f:
            json.dump(results, f, indent=2, default=str)
        
        self.logger.info(f"Results saved to: {output_file}")
        return output_file
    
    def print_summary(self, results: Dict[str, Any]):
        """Print a summary of test results."""
        print("\n" + "="*60)
        print("E-INK REFRESH TROUBLESHOOTING SUMMARY")
        print("="*60)
        
        # Hardware status
        hw = results['hardware_diagnostics']
        print(f"\n📊 Hardware Status:")
        print(f"  IT8951 Library: {'✅ Available' if hw['it8951_available'] else '❌ Not available'}")
        print(f"  Driver Mode: {'🧪 Mock' if hw['driver_mock_mode'] else '🔧 Hardware'}")
        print(f"  Hardware Init: {'✅ Success' if hw['hardware_initialized'] else '❌ Failed'}")
        print(f"  Direct Access: {'✅ Available' if hw['direct_access'] else '❌ Not available'}")
        
        if 'current_vcom' in hw:
            print(f"  Current VCOM: {hw['current_vcom']}V")
        
        # Test results summary
        total = results['total_tests']
        successful = results['successful_tests']
        if total > 0:
            print(f"\n📈 Test Results: {successful}/{total} tests passed ({successful/total*100:.1f}%)")
        else:
            print(f"\n📈 Test Results: No tests were run")
        
        # Display modes
        successful_modes = results.get('successful_modes', [])
        failed_modes = results.get('failed_modes', [])
        if successful_modes or failed_modes:
            print(f"\n🎨 Display Modes:")
            for mode in successful_modes:
                print(f"  ✅ {mode}")
            for mode in failed_modes:
                print(f"  ❌ {mode}")
        
        # Recovery
        recovery = results.get('recovery_success', False)
        print(f"\n🔧 Recovery Test: {'✅ Successful' if recovery else '❌ Failed'}")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        if not hw['it8951_available']:
            print("  • Install IT8951 library: pip install IT8951")
        
        if not hw['hardware_initialized'] and not hw['driver_mock_mode']:
            print("  • Check SPI connections and permissions")
            print("  • Verify display power and reset connections")
            
        if failed_modes:
            print("  • Some display modes failed - check power supply stability")
            print("  • Consider VCOM calibration if many modes fail")
        
        if not recovery:
            print("  • Display may need manual reset or power cycle")
            print("  • Check for hardware connection issues")
        
        successful_vcom_tests = [k for k, v in results['test_results'].items() 
                               if k.startswith('vcom_') and v.get('success', False)]
        if successful_vcom_tests:
            print(f"  • {len(successful_vcom_tests)} VCOM values worked successfully")
        
        print(f"\n📄 Detailed results saved to troubleshooting log file")
        print("="*60)
    
    def cleanup(self):
        """Clean up resources."""
        try:
            if self.direct_display and hasattr(self.direct_display, 'close'):
                self.direct_display.close()
            self.driver.cleanup()
            self.logger.info("Cleanup completed")
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")


def main():
    """Main entry point for the troubleshooting utility."""
    parser = argparse.ArgumentParser(
        description='E-ink Display Refresh Troubleshooting Utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python troubleshoot_eink_refresh.py --all              # Run all tests
  python troubleshoot_eink_refresh.py --modes            # Test display modes only
  python troubleshoot_eink_refresh.py --vcom             # Test VCOM values only
  python troubleshoot_eink_refresh.py --screenshots      # Test screenshot rendering
  python troubleshoot_eink_refresh.py --recovery         # Run recovery procedure
  python troubleshoot_eink_refresh.py --diagnostics      # Hardware diagnostics only
        """
    )
    
    parser.add_argument('--all', action='store_true',
                       help='Run comprehensive troubleshooting tests')
    parser.add_argument('--modes', action='store_true',
                       help='Test all IT8951 display modes')
    parser.add_argument('--vcom', action='store_true',
                       help='Test different VCOM values')
    parser.add_argument('--screenshots', action='store_true',
                       help='Test rendering existing screenshots')
    parser.add_argument('--recovery', action='store_true',
                       help='Run display recovery procedure')
    parser.add_argument('--diagnostics', action='store_true',
                       help='Run hardware diagnostics only')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--output', '-o', type=Path,
                       help='Output file for detailed results')
    
    args = parser.parse_args()
    
    if not any([args.all, args.modes, args.vcom, args.screenshots, args.recovery, args.diagnostics]):
        args.all = True  # Default to comprehensive test
    
    print("E-ink Display Refresh Troubleshooting Utility")
    print("=" * 50)
    
    troubleshooter = EInkRefreshTroubleshooter(verbose=args.verbose)
    
    try:
        results = {}
        
        if args.all:
            results = troubleshooter.run_comprehensive_tests()
        else:
            # Run individual test categories
            if args.diagnostics or not args.all:
                results['hardware_diagnostics'] = troubleshooter.run_hardware_diagnostics()
            
            if args.modes:
                troubleshooter.logger.info("\n=== Display Mode Tests ===")
                for mode_name, description in troubleshooter.display_modes.items():
                    troubleshooter.test_display_mode(mode_name, description)
                    time.sleep(1)
                results['successful_modes'] = troubleshooter.successful_modes
                results['failed_modes'] = troubleshooter.failed_modes
            
            if args.vcom:
                troubleshooter.logger.info("\n=== VCOM Tests ===")
                original_vcom = troubleshooter.settings.it8951_vcom
                for vcom in troubleshooter.vcom_test_values:
                    troubleshooter.test_vcom_setting(vcom)
                    time.sleep(1)
                # Restore original VCOM
                if troubleshooter.direct_display:
                    try:
                        troubleshooter.direct_display.epd.set_vcom(original_vcom)
                    except Exception:
                        pass
            
            if args.screenshots:
                troubleshooter.logger.info("\n=== Screenshot Tests ===")
                screenshot_files = list(troubleshooter.screenshot_dir.glob("*.png"))
                for screenshot_path in screenshot_files[:3]:  # Limit to 3 files
                    troubleshooter.test_screenshot_rendering(screenshot_path)
                    time.sleep(1)
            
            if args.recovery:
                troubleshooter.logger.info("\n=== Recovery Test ===")
                recovery_success = troubleshooter.recover_from_failed_refresh()
                results['recovery_success'] = recovery_success
            
            # Compile partial results
            results.update({
                'test_results': troubleshooter.test_results,
                'total_tests': len(troubleshooter.test_results),
                'successful_tests': sum(1 for r in troubleshooter.test_results.values() if r.get('success', False)),
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        # Save detailed results
        output_file = troubleshooter.save_results(results, args.output)
        
        # Print summary
        troubleshooter.print_summary(results)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Troubleshooting interrupted by user")
    except Exception as e:
        print(f"\n❌ Troubleshooting failed with error: {e}")
        troubleshooter.logger.exception("Troubleshooting error")
        sys.exit(1)
    finally:
        troubleshooter.cleanup()
    
    print(f"\n🎉 Troubleshooting completed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
