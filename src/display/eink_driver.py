"""
E-ink display driver using omni-epd library for Waveshare 10.3" e-Paper HAT.
Provides a simplified interface using the omni-epd abstraction.
"""

import logging
import time
from PIL import Image

try:
    from omni_epd import displayfactory, EPDNotFoundError
    OMNI_EPD_AVAILABLE = True
except ImportError:
    OMNI_EPD_AVAILABLE = False
    logging.warning("omni-epd library not available - running in simulation mode")


class EInkDriver:
    """Driver for Waveshare 10.3" e-Paper display using omni-epd."""
    
    def __init__(self, settings):
        """Initialize the e-ink display driver."""
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Display state tracking
        self.partial_refresh_count = 0
        self.last_update_time = 0
        
        # Display object
        self.epd = None
        self.hardware_initialized = False
        
        if OMNI_EPD_AVAILABLE:
            self._init_display()
        else:
            self.logger.warning("Running in simulation mode - no actual display updates")
    
    def _init_display(self):
        """Initialize the omni-epd display."""
        try:
            self.logger.info(f"Initializing omni-epd display: {self.settings.epd_device}")
            
            # Load the display driver specified in settings (no implicit fallback)
            try:
                self.epd = displayfactory.load_display_driver(self.settings.epd_device)
            except (EPDNotFoundError, Exception) as e:
                self.logger.error(f"Failed to load display '{self.settings.epd_device}': {e}")
                raise
            
            if self.epd is None:
                raise EPDNotFoundError(f"Could not load display driver: {self.settings.epd_device}")
            
            # Log display information
            self.logger.info(f"Display loaded: {self.settings.epd_device}")
            self.logger.info(f"Display size: {self.epd.width}x{self.epd.height}")
            self.logger.info(f"Available modes: {getattr(self.epd, 'modes_available', ['bw'])}")
            
            # Verify display dimensions match settings
            if (self.epd.width != self.settings.display_width or 
                self.epd.height != self.settings.display_height):
                self.logger.warning(
                    f"Display size mismatch: expected {self.settings.display_width}x{self.settings.display_height}, "
                    f"got {self.epd.width}x{self.epd.height}"
                )
                
                self.logger.info("Updating settings to match hardware display dimensions")
                self.settings.display_width = self.epd.width
                self.settings.display_height = self.epd.height
            
            # Initialize the display
            self.epd.prepare()
            
            self.hardware_initialized = True
            self.logger.info("E-ink display initialized successfully")
            
        except EPDNotFoundError as e:
            self.logger.error(f"Display not found: {e}")
            self.hardware_initialized = False
        except Exception as e:
            self.logger.error(f"Failed to initialize display: {e}")
            self.hardware_initialized = False
    
    def update(self, image, force_full_refresh=False):
        """Update the display with a new image."""
        try:
            if image is None:
                self.logger.error("Cannot update display with None image")
                return False
            
            # Check if we need a full refresh
            need_full_refresh = (
                force_full_refresh or 
                self.partial_refresh_count >= self.settings.eink_partial_refresh_limit
            )
            
            if not OMNI_EPD_AVAILABLE:
                # Update refresh counter for simulation too
                if need_full_refresh:
                    self.partial_refresh_count = 0
                else:
                    self.partial_refresh_count += 1
                return self._simulate_update(image, need_full_refresh)
            
            if not self.hardware_initialized:
                self.logger.error("Hardware not initialized")
                return False
            
            self.logger.info(f"Updating display ({'full' if need_full_refresh else 'partial'} refresh, count: {self.partial_refresh_count})")
            
            # Process image for display
            processed_image = self._process_image(image)
            
            # Update the display
            if self.epd:
                self.epd.display(processed_image)
            
            # Update refresh counter AFTER successful display update
            if need_full_refresh:
                self.partial_refresh_count = 0
                self.logger.info("Full refresh completed, reset partial refresh count to 0")
            else:
                self.partial_refresh_count += 1
                self.logger.debug(f"Partial refresh completed, count now: {self.partial_refresh_count}")
            
            self.last_update_time = time.time()
            self.logger.info("Display update completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating display: {e}")
            return False
    
    def _process_image(self, image):
        """Process image for optimal display on e-ink."""
        try:
            # Ensure correct size
            if image.size != (self.settings.display_width, self.settings.display_height):
                self.logger.debug(f"Resizing image from {image.size} to {self.settings.display_width}x{self.settings.display_height}")
                image = image.resize(
                    (self.settings.display_width, self.settings.display_height),
                    Image.Resampling.LANCZOS
                )
            
            # Convert to appropriate mode based on display capabilities
            # Note: For BW displays, we keep the image in grayscale mode 'L' 
            # so that omni-epd can apply dithering before final conversion
            if self.settings.epd_mode == "gray16":
                # Convert to grayscale for 16-level gray displays
                if image.mode != 'L':
                    image = image.convert('L')
            else:
                # For BW displays, ensure grayscale mode for dithering
                if image.mode != 'L':
                    image = image.convert('L')
                # Let omni-epd handle the final conversion to 1-bit after dithering
            
            return image
            
        except Exception as e:
            self.logger.error(f"Error processing image: {e}")
            return image
    
    def _simulate_update(self, image, full_refresh):
        """Simulate display update when hardware is not available."""
        refresh_type = "full" if full_refresh else "partial"
        self.logger.info(f"SIMULATION: Display update ({refresh_type} refresh)")
        self.logger.info(f"SIMULATION: Image size: {image.size}, mode: {image.mode}")
        
        # Save image for debugging
        try:
            timestamp = int(time.time())
            filename = f"display_update_{timestamp}_{refresh_type}.png"
            filepath = self.settings.temp_dir / filename
            image.save(filepath)
            self.logger.info(f"SIMULATION: Saved display image to {filepath}")
        except Exception as e:
            self.logger.warning(f"Could not save simulation image: {e}")
        
        return True
    
    def clear_display(self):
        """Clear the display to white."""
        try:
            self.logger.info("Clearing display")
            
            if not OMNI_EPD_AVAILABLE or not self.hardware_initialized:
                self.logger.info("SIMULATION: Display cleared")
                return True
            
            # Use omni-epd's clear method if available
            if self.epd and hasattr(self.epd, 'clear'):
                self.epd.clear()
            elif self.epd:
                # Create white image and display it
                white_image = Image.new('1' if self.settings.epd_mode == 'bw' else 'L', 
                                      (self.settings.display_width, self.settings.display_height), 
                                      255)
                self.epd.display(white_image)
            
            self.partial_refresh_count = 0  # Reset counter after clear
            return True
            
        except Exception as e:
            self.logger.error(f"Error clearing display: {e}")
            return False
    
    def sleep(self):
        """Put the display into sleep mode."""
        try:
            if not OMNI_EPD_AVAILABLE or not self.hardware_initialized:
                self.logger.info("SIMULATION: Display put to sleep")
                return
                
            self.logger.info("Putting display to sleep")
            
            if self.epd and hasattr(self.epd, 'sleep'):
                self.epd.sleep()
            else:
                self.logger.warning("Sleep method not available for this display")
                
        except Exception as e:
            self.logger.error(f"Error putting display to sleep: {e}")
    
    def cleanup(self):
        """Clean up display resources."""
        try:
            if OMNI_EPD_AVAILABLE and self.hardware_initialized and self.epd:
                self.logger.info("Cleaning up display resources")
                
                # Put display to sleep
                self.sleep()
                
                # Close the display
                if hasattr(self.epd, 'close'):
                    self.epd.close()
                
                self.hardware_initialized = False
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def test_display(self):
        """Test the display with a simple pattern."""
        try:
            self.logger.info("Testing display")
            
            # Create a simple test pattern
            test_image = Image.new('RGB', 
                                 (self.settings.display_width, self.settings.display_height), 
                                 (255, 255, 255)) # type: ignore
            
            # Add some test content
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(test_image)
            
            # Try to load a font, fall back to default
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
            except (OSError, IOError):
                font = ImageFont.load_default()
            
            # Draw test text
            draw.text((20, 20), "Pi Home Dashboard", fill='black', font=font)
            draw.text((20, 60), f"Display Test - {self.settings.epd_device}", fill='black', font=font)
            draw.text((20, 100), f"Size: {self.settings.display_width}x{self.settings.display_height}", fill='black', font=font)
            draw.text((20, 140), f"Mode: {self.settings.epd_mode}", fill='black', font=font)
            
            # Draw a border
            draw.rectangle([10, 10, self.settings.display_width-10, self.settings.display_height-10], 
                         outline='black', width=5)
            
            # Update display
            return self.update(test_image, force_full_refresh=True)
            
        except Exception as e:
            self.logger.error(f"Error testing display: {e}")
            return False
    
    @property
    def width(self):
        """Get display width."""
        return self.settings.display_width
    
    @property
    def height(self):
        """Get display height."""
        return self.settings.display_height
    
    @property
    def is_available(self):
        """Check if display hardware is available."""
        return OMNI_EPD_AVAILABLE and self.hardware_initialized
