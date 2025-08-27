"""
IT8951 E-ink display driver using GregDMeyer/IT8951 library.
Provides direct control over IT8951 controller for enhanced partial refresh capabilities.
"""

import logging
import time
import os
from PIL import Image
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
