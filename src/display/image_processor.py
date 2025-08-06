"""
Image processing utilities for e-ink display optimization.
Handles image conversion, dithering, and test image generation.
"""

import logging
from PIL import Image, ImageDraw, ImageFont
import numpy as np


class ImageProcessor:
    """Image processing class for e-ink display optimization."""
    
    def __init__(self, settings):
        """Initialize the image processor."""
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
    def process_for_eink(self, image):
        """Process an image for optimal e-ink display."""
        try:
            if image is None:
                self.logger.error("Cannot process None image")
                return None
                
            self.logger.info("Processing image for e-ink display")
            
            # Resize image to display dimensions if needed
            if image.size != (self.settings.display_width, self.settings.display_height):
                self.logger.info(f"Resizing image from {image.size} to {self.settings.display_width}x{self.settings.display_height}")
                image = image.resize(
                    (self.settings.display_width, self.settings.display_height),
                    Image.Resampling.LANCZOS
                )
            
            # Convert to grayscale
            if image.mode != 'L':
                self.logger.info("Converting image to grayscale")
                image = image.convert('L')
            
            # Apply rotation if specified
            if self.settings.display_rotation != 0:
                self.logger.info(f"Rotating image by {self.settings.display_rotation} degrees")
                image = image.rotate(self.settings.display_rotation, expand=True)
            
            # Apply dithering for better e-ink display
            image = self._apply_dithering(image)
            
            self.logger.info("Image processing completed")
            return image
            
        except Exception as e:
            self.logger.error(f"Error processing image: {e}")
            return None
    
    def _apply_dithering(self, image):
        """Apply Floyd-Steinberg dithering for better e-ink display."""
        try:
            self.logger.debug("Applying Floyd-Steinberg dithering")
            
            # Convert to numpy array for processing
            img_array = np.array(image, dtype=np.float32)
            height, width = img_array.shape
            
            # Floyd-Steinberg dithering
            for y in range(height - 1):
                for x in range(1, width - 1):
                    old_pixel = img_array[y, x]
                    new_pixel = 255 if old_pixel > 127 else 0
                    img_array[y, x] = new_pixel
                    
                    error = old_pixel - new_pixel
                    
                    # Distribute error to neighboring pixels
                    img_array[y, x + 1] += error * 7 / 16
                    img_array[y + 1, x - 1] += error * 3 / 16
                    img_array[y + 1, x] += error * 5 / 16
                    img_array[y + 1, x + 1] += error * 1 / 16
            
            # Convert back to PIL Image
            img_array = np.clip(img_array, 0, 255).astype(np.uint8)
            return Image.fromarray(img_array, mode='L')
            
        except Exception as e:
            self.logger.error(f"Error applying dithering: {e}")
            return image  # Return original image if dithering fails
    
    def create_test_image(self):
        """Create a test image for display testing."""
        try:
            self.logger.info("Creating test image")
            
            # Create white background
            image = Image.new('RGB', 
                            (self.settings.display_width, self.settings.display_height))
            image.paste((255, 255, 255), (0, 0, self.settings.display_width, self.settings.display_height))
            
            draw = ImageDraw.Draw(image)
            
            # Try to load a font, fall back to default if not available
            try:
                font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
                font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
                font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            except (OSError, IOError):
                self.logger.warning("Could not load custom fonts, using default")
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            # Draw test content
            y_pos = 50
            
            # Title
            draw.text((50, y_pos), "Pi Home Dashboard - Test Display", 
                     fill=(0, 0, 0), font=font_large)
            y_pos += 80
            
            # Display info
            draw.text((50, y_pos), f"Display Resolution: {self.settings.display_width} x {self.settings.display_height}", 
                     fill=(0, 0, 0), font=font_medium)
            y_pos += 40
            
            # Test patterns
            draw.text((50, y_pos), "Test Patterns:", fill=(0, 0, 0), font=font_medium)
            y_pos += 50
            
            # Draw rectangles with different shades
            rect_width = 100
            rect_height = 50
            x_start = 50
            
            shades = [0, 64, 128, 192, 255]  # Black to white
            for i, shade in enumerate(shades):
                x = x_start + i * (rect_width + 10)
                draw.rectangle([x, y_pos, x + rect_width, y_pos + rect_height], 
                             fill=(shade, shade, shade), outline=(0, 0, 0))
                draw.text((x + 10, y_pos + rect_height + 10), f"{shade}", 
                         fill=(0, 0, 0), font=font_small)
            
            y_pos += rect_height + 60
            
            # Draw grid pattern
            draw.text((50, y_pos), "Grid Pattern:", fill=(0, 0, 0), font=font_medium)
            y_pos += 40
            
            grid_size = 20
            for i in range(0, 200, grid_size):
                for j in range(0, 100, grid_size):
                    x = 50 + i
                    y = y_pos + j
                    if (i // grid_size + j // grid_size) % 2 == 0:
                        draw.rectangle([x, y, x + grid_size, y + grid_size], 
                                     fill=(0, 0, 0))
            
            y_pos += 120
            
            # System info
            draw.text((50, y_pos), "System: Raspberry Pi Zero 2 W", 
                     fill=(0, 0, 0), font=font_medium)
            y_pos += 30
            draw.text((50, y_pos), "Display: Waveshare 10.3\" e-Paper HAT", 
                     fill=(0, 0, 0), font=font_medium)
            y_pos += 30
            draw.text((50, y_pos), "Interface: SPI GPIO", 
                     fill=(0, 0, 0), font=font_medium)
            
            # Draw border
            draw.rectangle([0, 0, self.settings.display_width - 1, self.settings.display_height - 1], 
                         outline=(0, 0, 0), width=3)
            
            # Process for e-ink display
            processed_image = self.process_for_eink(image)
            
            self.logger.info("Test image created successfully")
            return processed_image
            
        except Exception as e:
            self.logger.error(f"Error creating test image: {e}")
            return None
    
    def save_image(self, image, filename):
        """Save an image to file for debugging."""
        try:
            if image is None:
                self.logger.error("Cannot save None image")
                return False
                
            filepath = self.settings.temp_dir / filename
            image.save(filepath)
            self.logger.info(f"Image saved to {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving image: {e}")
            return False
