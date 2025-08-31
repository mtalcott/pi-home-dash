"""
IT8951 E-ink display driver using GregDMeyer/IT8951 library.
Provides direct control over IT8951 controller for enhanced partial refresh capabilities.
"""

import logging
import time
import os
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Tuple, Union

try:
    from IT8951.display import AutoEPDDisplay
    from IT8951 import constants
    IT8951_AVAILABLE = True
except ImportError:
    IT8951_AVAILABLE = False
    logging.warning("IT8951 library not available - running in simulation mode")


class IT8951Driver:
    """Driver for IT8951-based e-Paper displays with enhanced partial refresh control."""
    
    def __init__(self, settings):
        """Initialize the IT8951 display driver."""
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Display state tracking
        self.partial_refresh_count = 0
        self.last_update_time = 0
        self.last_image = None
        
        # Display object
        self.display = None
        self.hardware_initialized = False
        
        # Mock mode detection
        self.mock_mode = settings.display_type == 'mock'
        
        if IT8951_AVAILABLE and not self.mock_mode:
            self._init_display()
        else:
            if self.mock_mode:
                self.logger.info("Running in mock display mode")
            else:
                self.logger.warning("Running in simulation mode - IT8951 library not available")
    
    def _init_display(self):
        """Initialize the IT8951 display."""
        try:
            self.logger.info("Initializing IT8951 display...")
            
            # Initialize the display with auto-detection
            self.display = AutoEPDDisplay(vcom=-2.06, rotate=None, spi_hz=24000000, mirror=True)
            
            if self.display is None:
                raise RuntimeError("Failed to initialize IT8951 display")
            
            # Log display information
            self.logger.info(f"Display initialized successfully")
            self.logger.info(f"Display size: {self.display.width}x{self.display.height}")
            self.logger.info(f"VCOM: {self.display.epd.get_vcom()}")
            
            # Verify display dimensions match settings
            if (self.display.width != self.settings.display_width or 
                self.display.height != self.settings.display_height):
                self.logger.warning(
                    f"Display size mismatch: expected {self.settings.display_width}x{self.settings.display_height}, "
                    f"got {self.display.width}x{self.display.height}"
                )
                
                self.logger.info("Updating settings to match hardware display dimensions")
                self.settings.display_width = self.display.width
                self.settings.display_height = self.display.height
            
            self.hardware_initialized = True
            self.logger.info("IT8951 display initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize IT8951 display: {e}")
            self.hardware_initialized = False
    
    def update(self, image: Image.Image, force_full_refresh: bool = False, region: Optional[Tuple[int, int, int, int]] = None) -> bool:
        """
        Update the display with a new image.
        
        Args:
            image: PIL Image to display
            force_full_refresh: Force a full refresh instead of partial
            region: Optional region tuple (x, y, width, height) for partial updates
            
        Returns:
            bool: True if update was successful
        """
        try:
            if image is None:
                self.logger.error("Cannot update display with None image")
                return False
            
            # Check if we need a full refresh
            need_full_refresh = (
                force_full_refresh or 
                self.partial_refresh_count >= self.settings.eink_partial_refresh_limit or
                self.last_image is None
            )
            
            if self.mock_mode or not IT8951_AVAILABLE:
                # Update refresh counter for simulation too
                if need_full_refresh:
                    self.partial_refresh_count = 0
                else:
                    self.partial_refresh_count += 1
                return self._simulate_update(image, need_full_refresh, region)
            
            if not self.hardware_initialized:
                self.logger.error("Hardware not initialized")
                return False
            
            refresh_type = "full" if need_full_refresh else "partial"
            region_str = f" region={region}" if region else ""
            self.logger.info(f"Updating display ({refresh_type} refresh{region_str}, count: {self.partial_refresh_count})")
            
            # Process image for display
            processed_image = self._process_image(image)
            
            # Perform the update
            start_time = time.time()
            
            if need_full_refresh:
                # Full refresh
                self.display.frame_buf.paste(processed_image, (0, 0))
                self.display.draw_full(constants.DisplayModes.GC16)
                self.partial_refresh_count = 0
                self.logger.info("Full refresh completed, reset partial refresh count to 0")
            else:
                # Partial refresh
                if region:
                    # Partial refresh with specific region
                    x, y, w, h = region
                    cropped_image = processed_image.crop((x, y, x + w, y + h))
                    self.display.frame_buf.paste(cropped_image, (x, y))
                    self.display.draw_partial(constants.DisplayModes.DU, (x, y, x + w, y + h))
                else:
                    # Full area partial refresh
                    self.display.frame_buf.paste(processed_image, (0, 0))
                    self.display.draw_partial(constants.DisplayModes.DU)
                
                self.partial_refresh_count += 1
                self.logger.debug(f"Partial refresh completed, count now: {self.partial_refresh_count}")
            
            duration = time.time() - start_time
            self.last_update_time = time.time()
            self.last_image = processed_image.copy()
            
            self.logger.info(f"Display update completed successfully in {duration:.2f}s")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating display: {e}")
            return False
    
    def update_partial_region(self, image: Image.Image, region: Tuple[int, int, int, int]) -> bool:
        """
        Update a specific region of the display with partial refresh.
        
        Args:
            image: Full-size PIL Image
            region: Region tuple (x, y, width, height)
            
        Returns:
            bool: True if update was successful
        """
        return self.update(image, force_full_refresh=False, region=region)
    
    def _process_image(self, image: Image.Image) -> Image.Image:
        """Process image for optimal display on IT8951."""
        try:
            # Ensure correct size
            if image.size != (self.settings.display_width, self.settings.display_height):
                self.logger.debug(f"Resizing image from {image.size} to {self.settings.display_width}x{self.settings.display_height}")
                image = image.resize(
                    (self.settings.display_width, self.settings.display_height),
                    Image.Resampling.LANCZOS
                )
            
            # Convert to grayscale if needed
            if image.mode != 'L':
                image = image.convert('L')
            
            return image
            
        except Exception as e:
            self.logger.error(f"Error processing image: {e}")
            return image
    
    def _simulate_update(self, image: Image.Image, full_refresh: bool, region: Optional[Tuple[int, int, int, int]] = None) -> bool:
        """Simulate display update when hardware is not available."""
        refresh_type = "full" if full_refresh else "partial"
        region_str = f" region={region}" if region else ""
        self.logger.info(f"SIMULATION: Display update ({refresh_type} refresh{region_str})")
        self.logger.info(f"SIMULATION: Image size: {image.size}, mode: {image.mode}")
        
        # Save image for debugging
        try:
            timestamp = int(time.time())
            region_suffix = f"_region_{region[0]}_{region[1]}_{region[2]}_{region[3]}" if region else ""
            filename = f"display_update_{timestamp}_{refresh_type}{region_suffix}.png"
            filepath = self.settings.temp_dir / filename
            
            if region:
                # Save only the region that would be updated
                x, y, w, h = region
                cropped_image = image.crop((x, y, x + w, y + h))
                cropped_image.save(filepath)
                self.logger.info(f"SIMULATION: Saved region image to {filepath}")
            else:
                image.save(filepath)
                self.logger.info(f"SIMULATION: Saved display image to {filepath}")
                
        except Exception as e:
            self.logger.warning(f"Could not save simulation image: {e}")
        
        # Simulate timing
        if full_refresh:
            time.sleep(0.5)  # Simulate full refresh time
        else:
            time.sleep(0.1)  # Simulate partial refresh time
        
        return True
    
    def clear_display(self) -> bool:
        """Clear the display to white."""
        try:
            self.logger.info("Clearing display")
            
            if self.mock_mode or not IT8951_AVAILABLE or not self.hardware_initialized:
                self.logger.info("SIMULATION: Display cleared")
                self.partial_refresh_count = 0
                return True
            
            # Create white image and display it
            white_image = Image.new('L', (self.settings.display_width, self.settings.display_height), 255)
            
            # Use full refresh for clearing
            self.display.frame_buf.paste(white_image, (0, 0))
            self.display.draw_full(constants.DisplayModes.GC16)
            self.partial_refresh_count = 0  # Reset counter after clear
            
            self.logger.info("Display cleared successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error clearing display: {e}")
            return False
    
    def sleep(self):
        """Put the display into sleep mode."""
        try:
            if self.mock_mode or not IT8951_AVAILABLE or not self.hardware_initialized:
                self.logger.info("SIMULATION: Display put to sleep")
                return
                
            self.logger.info("Putting display to sleep")
            
            if self.display and hasattr(self.display, 'sleep'):
                self.display.sleep()
            else:
                self.logger.warning("Sleep method not available for this display")
                
        except Exception as e:
            self.logger.error(f"Error putting display to sleep: {e}")
    
    def cleanup(self):
        """Clean up display resources."""
        try:
            if IT8951_AVAILABLE and self.hardware_initialized and self.display:
                self.logger.info("Cleaning up display resources")
                
                # Put display to sleep
                self.sleep()
                
                # Close the display
                if hasattr(self.display, 'close'):
                    self.display.close()
                
                self.hardware_initialized = False
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def test_display(self) -> bool:
        """Test the display with a simple pattern."""
        try:
            self.logger.info("Testing display")
            
            # Create a simple test pattern
            test_image = Image.new('RGB', 
                                 (self.settings.display_width, self.settings.display_height), 
                                 (255, 255, 255))
            
            # Add some test content
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(test_image)
            
            # Try to load a font, fall back to default
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 60)
            except (OSError, IOError):
                font = ImageFont.load_default()
            
            # Draw test text
            draw.text((40, 40), "Pi Home Dashboard", fill='black', font=font)
            draw.text((40, 120), f"Display Test - IT8951", fill='black', font=font)
            draw.text((40, 200), f"Size: {self.settings.display_width}x{self.settings.display_height}", fill='black', font=font)
            draw.text((40, 280), f"Partial refresh support: Enhanced", fill='black', font=font)
            
            # Draw a border
            draw.rectangle([10, 10, self.settings.display_width-10, self.settings.display_height-10], 
                         outline='black', width=5)
            
            # Update display
            return self.update(test_image, force_full_refresh=True)
            
        except Exception as e:
            self.logger.error(f"Error testing display: {e}")
            return False
    
    @property
    def width(self) -> int:
        """Get display width."""
        return self.settings.display_width
    
    @property
    def height(self) -> int:
        """Get display height."""
        return self.settings.display_height
    
    @property
    def is_available(self) -> bool:
        """Check if display hardware is available."""
        return (IT8951_AVAILABLE and self.hardware_initialized) or self.mock_mode
    
    @property
    def supports_partial_refresh(self) -> bool:
        """Check if display supports partial refresh."""
        return True  # IT8951 always supports partial refresh
    
    def get_refresh_stats(self) -> dict:
        """Get refresh statistics."""
        return {
            'partial_refresh_count': self.partial_refresh_count,
            'last_update_time': self.last_update_time,
            'hardware_initialized': self.hardware_initialized,
            'mock_mode': self.mock_mode,
            'supports_partial_refresh': self.supports_partial_refresh
        }
    
    # Utility methods for creating display content
    
    def _load_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        """Load a system font with fallback to default."""
        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation/LiberationSans.ttf',
            '/System/Library/Fonts/Arial.ttf',  # macOS
            'C:/Windows/Fonts/arial.ttf'  # Windows
        ]
        
        for font_path in font_paths:
            try:
                return ImageFont.truetype(font_path, size)
            except (OSError, IOError):
                continue
        
        # Fall back to default font
        return ImageFont.load_default()
    
    def create_text_image(self, text: str, font_size: int = 24, center: bool = True, 
                         add_timestamp: bool = True) -> Image.Image:
        """Create an image with text content.
        
        Args:
            text: Text to display
            font_size: Font size for main text
            center: Whether to center the text
            add_timestamp: Whether to add timestamp in corner
            
        Returns:
            PIL Image with text content
        """
        # Create white background (grayscale for e-ink)
        image = Image.new('L', (self.settings.display_width, self.settings.display_height), 255)
        draw = ImageDraw.Draw(image)
        
        # Load font
        font = self._load_font(font_size, bold=True)
        
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
        
        # Draw text (black on white for e-ink)
        draw.text((x, y), text, fill=0, font=font)
        
        # Add timestamp in corner if requested
        if add_timestamp:
            timestamp = time.strftime("%H:%M:%S")
            small_font = self._load_font(12)
            draw.text((10, self.settings.display_height - 25), timestamp, fill=0, font=small_font)
        
        return image
    
    def create_test_pattern(self, pattern_type: str = "grid") -> Image.Image:
        """Create various test patterns for display testing.
        
        Args:
            pattern_type: Type of pattern ("grid", "stripes", "checkerboard")
            
        Returns:
            PIL Image with test pattern
        """
        # Create white background (grayscale for e-ink)
        image = Image.new('L', (self.settings.display_width, self.settings.display_height), 255)
        draw = ImageDraw.Draw(image)
        
        if pattern_type == "grid":
            # Draw grid pattern
            step = 50
            for x in range(0, self.settings.display_width, step):
                draw.line([(x, 0), (x, self.settings.display_height)], fill=0, width=1)
            for y in range(0, self.settings.display_height, step):
                draw.line([(0, y), (self.settings.display_width, y)], fill=0, width=1)
                
        elif pattern_type == "stripes":
            # Draw horizontal stripes
            stripe_height = 20
            for y in range(0, self.settings.display_height, stripe_height * 2):
                draw.rectangle([0, y, self.settings.display_width, y + stripe_height], fill=0)
                
        elif pattern_type == "checkerboard":
            # Draw checkerboard pattern
            square_size = 30
            for x in range(0, self.settings.display_width, square_size):
                for y in range(0, self.settings.display_height, square_size):
                    if (x // square_size + y // square_size) % 2:
                        draw.rectangle([x, y, x + square_size, y + square_size], fill=0)
        
        # Add pattern label
        font = self._load_font(16, bold=True)
        draw.text((10, 10), f"Pattern: {pattern_type}", fill=128, font=font)  # Gray text
        
        return image
    
    def create_initializing_message(self, mode: str, timestamp: str) -> Image.Image:
        """Create an initializing message image.
        
        Args:
            mode: Display mode (e.g., "Dakboard", "Custom")
            timestamp: Friendly timestamp string
            
        Returns:
            PIL Image with initializing message
        """
        # Create white background (grayscale for e-ink)
        image = Image.new('L', (self.settings.display_width, self.settings.display_height), 255)
        draw = ImageDraw.Draw(image)
        
        # Load fonts
        font_large = self._load_font(24, bold=True)
        font_small = self._load_font(16)
        
        # Calculate text positioning
        title_text = "Initializing..."
        mode_text = f"{mode} mode"
        time_text = timestamp
        
        # Get text dimensions for centering
        title_bbox = draw.textbbox((0, 0), title_text, font=font_large)
        mode_bbox = draw.textbbox((0, 0), mode_text, font=font_small)
        time_bbox = draw.textbbox((0, 0), time_text, font=font_small)
        
        title_width = title_bbox[2] - title_bbox[0]
        mode_width = mode_bbox[2] - mode_bbox[0]
        time_width = time_bbox[2] - time_bbox[0]
        
        # Center text horizontally and position vertically
        center_x = self.settings.display_width // 2
        start_y = self.settings.display_height // 2 - 40
        
        # Draw the text (black on white for e-ink)
        draw.text((center_x - title_width // 2, start_y), title_text, fill=0, font=font_large)
        draw.text((center_x - mode_width // 2, start_y + 35), mode_text, fill=0, font=font_small)
        draw.text((center_x - time_width // 2, start_y + 60), time_text, fill=0, font=font_small)
        
        return image
    
    def display_text(self, text: str, font_size: int = 24, center: bool = True, 
                    force_full_refresh: bool = False) -> bool:
        """Display text on the e-ink display.
        
        Args:
            text: Text to display
            font_size: Font size
            center: Whether to center the text
            force_full_refresh: Whether to force full refresh
            
        Returns:
            bool: True if successful
        """
        try:
            image = self.create_text_image(text, font_size, center)
            return self.update(image, force_full_refresh=force_full_refresh)
        except Exception as e:
            self.logger.error(f"Error displaying text: {e}")
            return False
    
    def display_test_pattern(self, pattern_type: str = "grid", 
                           force_full_refresh: bool = True) -> bool:
        """Display a test pattern on the e-ink display.
        
        Args:
            pattern_type: Type of pattern to display
            force_full_refresh: Whether to force full refresh
            
        Returns:
            bool: True if successful
        """
        try:
            image = self.create_test_pattern(pattern_type)
            return self.update(image, force_full_refresh=force_full_refresh)
        except Exception as e:
            self.logger.error(f"Error displaying test pattern: {e}")
            return False
    
    def display_initializing_message(self, mode: str, timestamp: str) -> bool:
        """Display an initializing message on the e-ink display.
        
        Args:
            mode: Display mode
            timestamp: Friendly timestamp string
            
        Returns:
            bool: True if successful
        """
        try:
            image = self.create_initializing_message(mode, timestamp)
            return self.update(image, force_full_refresh=True)
        except Exception as e:
            self.logger.error(f"Error displaying initializing message: {e}")
            return False
    
    # Direct IT8951 access methods for advanced testing
    
    def direct_partial_refresh(self, image: Image.Image, 
                             display_mode: Optional[str] = None) -> bool:
        """Perform direct partial refresh using IT8951 library.
        
        Args:
            image: PIL Image to display
            display_mode: IT8951 display mode (defaults to DU for fast partial)
            
        Returns:
            bool: True if successful
        """
        if not IT8951_AVAILABLE or self.mock_mode or not self.hardware_initialized:
            self.logger.warning("Direct partial refresh not available")
            return False
        
        try:
            processed_image = self._process_image(image)
            mode = getattr(constants.DisplayModes, display_mode or 'DU')
            
            self.display.frame_buf.paste(processed_image, (0, 0))
            self.display.draw_partial(mode)
            
            self.partial_refresh_count += 1
            self.logger.info(f"Direct partial refresh completed (mode: {display_mode or 'DU'})")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in direct partial refresh: {e}")
            return False
    
    def direct_full_refresh(self, image: Image.Image, 
                          display_mode: Optional[str] = None) -> bool:
        """Perform direct full refresh using IT8951 library.
        
        Args:
            image: PIL Image to display
            display_mode: IT8951 display mode (defaults to GC16 for full refresh)
            
        Returns:
            bool: True if successful
        """
        if not IT8951_AVAILABLE or self.mock_mode or not self.hardware_initialized:
            self.logger.warning("Direct full refresh not available")
            return False
        
        try:
            processed_image = self._process_image(image)
            mode = getattr(constants.DisplayModes, display_mode or 'GC16')
            
            self.display.frame_buf.paste(processed_image, (0, 0))
            self.display.draw_full(mode)
            
            self.partial_refresh_count = 0
            self.logger.info(f"Direct full refresh completed (mode: {display_mode or 'GC16'})")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in direct full refresh: {e}")
            return False
