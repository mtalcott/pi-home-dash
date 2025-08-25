#!/usr/bin/env python3
"""
E-ink Display Test Utility

A comprehensive utility for testing e-ink display refresh modes, clearing display,
and displaying custom text. Helps debug partial vs full refresh issues.
"""

import argparse
import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.settings import Settings
from display.eink_driver import EInkDriver

try:
    from omni_epd import displayfactory, EPDNotFoundError
    OMNI_EPD_AVAILABLE = True
except ImportError:
    OMNI_EPD_AVAILABLE = False


class EInkTestUtility:
    """Utility class for testing e-ink display functionality."""
    
    def __init__(self):
        """Initialize the test utility."""
        self.settings = Settings()
        
        # Load .env file if it exists
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            self.settings.load_from_file(env_file)
            print(f"✅ Loaded configuration from {env_file}")
        
        self.driver = EInkDriver(self.settings)
        self.epd = None
        
        # Initialize direct omni-epd access for advanced testing
        if OMNI_EPD_AVAILABLE:
            try:
                self.epd = displayfactory.load_display_driver(self.settings.epd_device)
                if self.epd:
                    self.epd.prepare()
                    print(f"✅ Direct omni-epd access initialized: {self.settings.epd_device}")
                    print(f"   Display size: {self.epd.width}x{self.epd.height}")
                    
                    # Check available methods
                    methods = []
                    if hasattr(self.epd, 'display_partial'):
                        methods.append('display_partial')
                    if hasattr(self.epd, 'display_full'):
                        methods.append('display_full')
                    if hasattr(self.epd, 'display'):
                        methods.append('display')
                    if hasattr(self.epd, 'clear'):
                        methods.append('clear')
                    
                    print(f"   Available methods: {', '.join(methods)}")
                    
            except Exception as e:
                print(f"⚠️  Could not initialize direct omni-epd access: {e}")
                self.epd = None
    
    def create_text_image(self, text, font_size=24, center=True):
        """Create an image with centered text."""
        # Create white background
        image = Image.new('RGB', (self.settings.display_width, self.settings.display_height), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # Try to load a font
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", font_size)
            except (OSError, IOError):
                font = ImageFont.load_default()
        
        # Calculate text position
        if center:
            # Get text bounding box
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (self.settings.display_width - text_width) // 2
            y = (self.settings.display_height - text_height) // 2
        else:
            x, y = 20, 20
        
        # Draw text
        draw.text((x, y), text, fill='black', font=font)
        
        # Add timestamp in corner
        timestamp = time.strftime("%H:%M:%S")
        try:
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except (OSError, IOError):
            small_font = ImageFont.load_default()
        
        draw.text((10, self.settings.display_height - 25), timestamp, fill='black', font=small_font)
        
        return image
    
    def create_test_pattern(self, pattern_type="grid"):
        """Create various test patterns."""
        image = Image.new('RGB', (self.settings.display_width, self.settings.display_height), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        if pattern_type == "grid":
            # Draw grid pattern
            step = 50
            for x in range(0, self.settings.display_width, step):
                draw.line([(x, 0), (x, self.settings.display_height)], fill='black', width=1)
            for y in range(0, self.settings.display_height, step):
                draw.line([(0, y), (self.settings.display_width, y)], fill='black', width=1)
                
        elif pattern_type == "stripes":
            # Draw horizontal stripes
            stripe_height = 20
            for y in range(0, self.settings.display_height, stripe_height * 2):
                draw.rectangle([0, y, self.settings.display_width, y + stripe_height], fill='black')
                
        elif pattern_type == "checkerboard":
            # Draw checkerboard pattern
            square_size = 30
            for x in range(0, self.settings.display_width, square_size):
                for y in range(0, self.settings.display_height, square_size):
                    if (x // square_size + y // square_size) % 2:
                        draw.rectangle([x, y, x + square_size, y + square_size], fill='black')
        
        # Add pattern label
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        except (OSError, IOError):
            font = ImageFont.load_default()
        
        draw.text((10, 10), f"Pattern: {pattern_type}", fill='red', font=font)
        
        return image
    
    def test_full_refresh(self, font_size=72):
        """Test full refresh mode."""
        print("\n🔄 Testing FULL refresh...")
        
        # Create test image
        image = self.create_text_image("FULL REFRESH TEST", font_size=font_size)
        
        # Force full refresh using driver
        start_time = time.time()
        success = self.driver.update(image, force_full_refresh=True)
        duration = time.time() - start_time
        
        if success:
            print(f"✅ Full refresh completed in {duration:.2f}s")
        else:
            print(f"❌ Full refresh failed")
        
        return success
    
    def test_partial_refresh(self, font_size=72):
        """Test partial refresh mode."""
        print("\n⚡ Testing PARTIAL refresh...")
        
        # Create test image with timestamp to show changes
        image = self.create_text_image(f"PARTIAL REFRESH\n{time.strftime('%H:%M:%S')}", font_size=font_size)
        
        # Use partial refresh (don't force full)
        start_time = time.time()
        success = self.driver.update(image, force_full_refresh=False)
        duration = time.time() - start_time
        
        if success:
            print(f"✅ Partial refresh completed in {duration:.2f}s")
        else:
            print(f"❌ Partial refresh failed")
        
        return success
    
    def test_direct_partial_refresh(self, font_size=72):
        """Test direct partial refresh using omni-epd if available."""
        if not self.epd or not hasattr(self.epd, 'display_partial'):
            print("\n⚠️  Direct partial refresh not available")
            return False
        
        print("\n⚡ Testing DIRECT partial refresh...")
        
        # Create test image
        image = self.create_text_image(f"DIRECT PARTIAL\n{time.strftime('%H:%M:%S')}", font_size=font_size)
        processed_image = self.driver._process_image(image)
        
        # Use direct partial refresh
        start_time = time.time()
        try:
            self.epd.display_partial(processed_image)
            duration = time.time() - start_time
            print(f"✅ Direct partial refresh completed in {duration:.2f}s")
            return True
        except Exception as e:
            print(f"❌ Direct partial refresh failed: {e}")
            return False
    
    def test_direct_full_refresh(self, font_size=72):
        """Test direct full refresh using omni-epd if available."""
        if not self.epd:
            print("\n⚠️  Direct full refresh not available")
            return False
        
        print("\n🔄 Testing DIRECT full refresh...")
        
        # Create test image
        image = self.create_text_image("DIRECT FULL REFRESH", font_size=font_size)
        processed_image = self.driver._process_image(image)
        
        # Use direct full refresh
        start_time = time.time()
        try:
            if hasattr(self.epd, 'display_full'):
                self.epd.display_full(processed_image)
            else:
                # Fall back to regular display method
                self.epd.display(processed_image)
            
            duration = time.time() - start_time
            print(f"✅ Direct full refresh completed in {duration:.2f}s")
            return True
        except Exception as e:
            print(f"❌ Direct full refresh failed: {e}")
            return False
    
    def clear_display(self):
        """Clear the display to white."""
        print("\n🧹 Clearing display...")
        
        start_time = time.time()
        success = self.driver.clear_display()
        duration = time.time() - start_time
        
        if success:
            print(f"✅ Display cleared in {duration:.2f}s")
        else:
            print(f"❌ Failed to clear display")
        
        return success
    
    def display_custom_text(self, text, font_size=24):
        """Display custom text on the display."""
        print(f"\n📝 Displaying custom text: '{text}'")
        
        # Create image with custom text
        image = self.create_text_image(text, font_size=font_size)
        
        # Update display with partial refresh
        start_time = time.time()
        success = self.driver.update(image, force_full_refresh=False)
        duration = time.time() - start_time
        
        if success:
            print(f"✅ Custom text displayed in {duration:.2f}s")
        else:
            print(f"❌ Failed to display custom text")
        
        return success
    
    def test_pattern(self, pattern_type):
        """Display a test pattern."""
        print(f"\n🎨 Displaying {pattern_type} pattern...")
        
        # Create pattern image
        image = self.create_test_pattern(pattern_type)
        
        # Update display
        start_time = time.time()
        success = self.driver.update(image, force_full_refresh=True)
        duration = time.time() - start_time
        
        if success:
            print(f"✅ {pattern_type} pattern displayed in {duration:.2f}s")
        else:
            print(f"❌ Failed to display {pattern_type} pattern")
        
        return success
    
    def run_refresh_comparison(self, font_size=72):
        """Run a comparison between full and partial refresh."""
        print("\n🔬 Running refresh comparison test...")
        
        # Test 1: Full refresh
        print("\n--- Test 1: Full Refresh ---")
        self.test_full_refresh(font_size)
        time.sleep(2)
        
        # Test 2: Partial refresh
        print("\n--- Test 2: Partial Refresh ---")
        self.test_partial_refresh(font_size)
        time.sleep(2)
        
        # Test 3: Direct partial refresh (if available)
        print("\n--- Test 3: Direct Partial Refresh ---")
        self.test_direct_partial_refresh(font_size)
        time.sleep(2)
        
        # Test 4: Multiple partial refreshes
        print("\n--- Test 4: Multiple Partial Refreshes ---")
        for i in range(3):
            print(f"  Partial refresh {i+1}/3...")
            image = self.create_text_image(f"PARTIAL #{i+1}\n{time.strftime('%H:%M:%S')}", font_size=font_size)
            self.driver.update(image, force_full_refresh=False)
            time.sleep(1)
        
        print("\n✅ Refresh comparison test completed")
    
    def cleanup(self):
        """Clean up resources."""
        try:
            if self.epd and hasattr(self.epd, 'close'):
                self.epd.close()
            self.driver.cleanup()
            print("✅ Cleanup completed")
        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='E-ink Display Test Utility')
    parser.add_argument('--full-refresh', action='store_true',
                       help='Test full refresh mode')
    parser.add_argument('--partial-refresh', action='store_true',
                       help='Test partial refresh mode')
    parser.add_argument('--direct-partial', action='store_true',
                       help='Test direct partial refresh (omni-epd)')
    parser.add_argument('--direct-full', action='store_true',
                       help='Test direct full refresh (omni-epd)')
    parser.add_argument('--clear', action='store_true',
                       help='Clear the display')
    parser.add_argument('--text', type=str,
                       help='Display custom text')
    parser.add_argument('--font-size', type=int, default=72,
                       help='Font size for text (default: 72)')
    parser.add_argument('--pattern', choices=['grid', 'stripes', 'checkerboard'],
                       help='Display test pattern')
    parser.add_argument('--compare', action='store_true',
                       help='Run refresh comparison test')
    parser.add_argument('--all', action='store_true',
                       help='Run all tests')
    
    args = parser.parse_args()
    
    print("E-ink Display Test Utility")
    print("=" * 50)
    
    # Create utility instance
    utility = EInkTestUtility()
    
    try:
        if args.all:
            # Run all tests with specified font size
            utility.clear_display()
            time.sleep(1)
            utility.test_full_refresh(args.font_size)
            time.sleep(2)
            utility.test_partial_refresh(args.font_size)
            time.sleep(2)
            utility.test_direct_partial_refresh(args.font_size)
            time.sleep(2)
            utility.test_pattern('grid')
            time.sleep(2)
            utility.run_refresh_comparison(args.font_size)
            
        elif args.compare:
            utility.run_refresh_comparison(args.font_size)
            
        elif args.clear:
            utility.clear_display()
            
        elif args.full_refresh:
            utility.test_full_refresh(args.font_size)
            
        elif args.partial_refresh:
            utility.test_partial_refresh(args.font_size)
            
        elif args.direct_partial:
            utility.test_direct_partial_refresh(args.font_size)
            
        elif args.direct_full:
            utility.test_direct_full_refresh(args.font_size)
            
        elif args.text:
            utility.display_custom_text(args.text, args.font_size)
            
        elif args.pattern:
            utility.test_pattern(args.pattern)
            
        else:
            # Default: show help and run basic test
            parser.print_help()
            print("\nRunning basic display test...")
            utility.test_full_refresh(args.font_size)
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)
    
    finally:
        utility.cleanup()
    
    print("\n🎉 Test utility completed!")


if __name__ == "__main__":
    main()
