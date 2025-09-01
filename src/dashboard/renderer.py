"""
Dashboard renderer for Pi Home Dashboard.
Handles rendering of dashboard content using headless browser or custom layouts.
"""

import asyncio
import logging
import tempfile
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from typing import Optional
from datetime import datetime

from playwright.async_api import async_playwright, BrowserContext, Page


class DashboardRenderer:
    """Main dashboard rendering class."""
    
    def __init__(self, settings):
        """Initialize the dashboard renderer."""
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Persistent browser state
        self.playwright = None
        self.context = None
        self.page = None
        self.is_persistent_browser_running = False
        self.current_url = None
        self.loop = None
        
        # Browser configuration
        self.user_data_dir = Path(settings.project_root) / ".cache" / "chromium_profile"
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Optimized Chrome arguments for Pi Zero 2 W
        self.chrome_args = [
            '--headless=new',
            '--disable-gpu',
            '--no-sandbox',
            '--disable-dev-shm-usage',  # Critical for Pi Zero 2 W
            '--disable-extensions',
            '--disable-plugins',
            '--disable-background-networking',
            '--disable-renderer-backgrounding',
            '--disable-background-timer-throttling',
            '--disable-features=Translate,BackForwardCache,AcceptCHFrame,MediaRouter,OptimizationHints,PaintHolding',
            '--hide-scrollbars',
            '--mute-audio',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-software-rasterizer',
            '--disk-cache-size=0',
            '--memory-pressure-off',
            '--max_old_space_size=256',  # Limit V8 heap for Pi
        ]
        
    def render(self):
        """Render the dashboard and return a PIL Image."""
        try:
            image = None
            if self.settings.dashboard_type == "dakboard":
                image = self._render_dakboard()
            elif self.settings.dashboard_type == "custom":
                image = self._render_custom()
            elif self.settings.dashboard_type == "integration_test":
                image = self._render_integration_test()
            else:
                raise ValueError(f"Unknown dashboard type: {self.settings.dashboard_type}")
            
            # Add timestamp overlay if debug mode is enabled and we have an image
            if image and self.settings.debug_mode:
                image = self._add_timestamp_overlay(image)
                
            return image
                
        except Exception as e:
            self.logger.error(f"Error rendering dashboard: {e}")
            return None
    
    def _render_dakboard(self):
        """Render DAKboard using persistent browser."""
        if not self.settings.dakboard_url:
            self.logger.error("DAKboard URL not configured")
            return None

        self.logger.info(f"Rendering DAKboard from URL: {self.settings.dakboard_url}")
        
        # Start persistent browser if not running
        if not self.is_persistent_browser_running:
            if not self.start_persistent_browser(self.settings.dakboard_url):
                self.logger.error("Failed to start persistent browser")
                return None
        
        # Take screenshot using persistent browser
        return self.render_persistent_screenshot()
    
    def _render_integration_test(self):
        """Render integration test dashboard using persistent browser."""
        self.logger.info("Rendering integration test dashboard")

        if not hasattr(self.settings, 'test_html_path') or self.settings.test_html_path is None:
            self.logger.error("Integration test HTML path not configured")
            return None

        if not self.settings.test_html_path.exists():
            self.logger.error(f"Integration test HTML file not found: {self.settings.test_html_path}")
            return None

        file_url = f"file://{self.settings.test_html_path.absolute()}"
        self.logger.info(f"Rendering integration test from: {file_url}")

        # Start persistent browser if not running
        if not self.is_persistent_browser_running:
            if not self.start_persistent_browser(file_url):
                self.logger.error("Failed to start persistent browser")
                return None
        
        # Take screenshot using persistent browser
        return self.render_persistent_screenshot()
    
    def _render_custom(self):
        """Render custom dashboard layout."""
        try:
            self.logger.info("Rendering custom dashboard")
            
            # Create a blank image with display dimensions
            image = Image.new('RGB', 
                            (self.settings.display_width, self.settings.display_height))
            # Fill with white background
            image.paste((255, 255, 255), (0, 0, self.settings.display_width, self.settings.display_height))
            
            # TODO: Implement custom dashboard rendering
            # This would involve:
            # 1. Fetching calendar data
            # 2. Fetching weather data
            # 3. Fetching to-do data
            # 4. Creating a custom layout
            # 5. Drawing text and graphics on the image
            
            self.logger.warning("Custom dashboard rendering not yet implemented")
            return image
            
        except Exception as e:
            self.logger.error(f"Error rendering custom dashboard: {e}")
            return None

    def start_persistent_browser(self, url: str) -> bool:
        """Start a persistent browser instance for faster subsequent renders."""
        try:
            self.logger.info("Starting persistent browser...")
            
            # Create event loop if needed
            if self.loop is None:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
            
            # Start the persistent browser
            success = self.loop.run_until_complete(self._start_persistent_browser_async(url))
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to start persistent browser: {e}")
            return False
    
    async def _start_persistent_browser_async(self, url: str) -> bool:
        """Async method to start persistent browser."""
        try:
            # Initialize Playwright
            self.playwright = await async_playwright().start()
            
            # Launch persistent context
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                headless=True,
                args=self.chrome_args,
                viewport={
                    "width": self.settings.browser_width,
                    "height": self.settings.browser_height
                },
                accept_downloads=False,
                ignore_https_errors=True,
            )
            
            # Get or create page
            self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            
            # Set timeouts
            self.page.set_default_navigation_timeout(180_000)  # 3 minutes
            self.page.set_default_timeout(60_000)  # 1 minute
            
            # Load the initial page
            self.logger.info(f"Loading initial page: {url}")
            await self.page.goto(url, wait_until="networkidle")
            
            # Optimize for e-ink display
            await self._optimize_page_for_eink()
            
            # Take initial screenshot to verify everything works
            test_path = self.user_data_dir / "test_screenshot.png"
            await self.page.screenshot(path=str(test_path))
            
            if test_path.exists():
                test_path.unlink()  # Clean up test file
                self.is_persistent_browser_running = True
                self.current_url = url
                self.logger.info("Persistent browser started successfully")
                return True
            else:
                self.logger.error("Failed to take initial screenshot")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to start persistent browser: {e}")
            await self._cleanup_persistent_browser()
            return False
    
    async def _optimize_page_for_eink(self):
        """Optimize the page for e-ink display rendering."""
        try:
            # Disable animations and transitions
            await self.page.add_style_tag(content="""
                * { 
                    animation: none !important; 
                    transition: none !important; 
                    animation-duration: 0s !important;
                    transition-duration: 0s !important;
                }
                video, audio { 
                    display: none !important; 
                }
                .slideshow, .carousel {
                    animation: none !important;
                }
            """)
            
            # Ensure proper scroll position and zoom
            await self.page.evaluate("""
                window.scrollTo(0, 0);
                document.body.style.zoom = '100%';
                document.documentElement.style.zoom = '100%';
            """)
            
            self.logger.debug("Page optimized for e-ink display")
            
        except Exception as e:
            self.logger.warning(f"Failed to optimize page: {e}")
    
    def render_persistent_screenshot(self) -> Optional[Image.Image]:
        """Take a screenshot using the persistent browser."""
        if not self.is_persistent_browser_running or not self.loop:
            self.logger.error("Persistent browser not running")
            return None
        
        try:
            # Create temporary file for screenshot
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_path = Path(temp_file.name)
            
            # Take screenshot using async method
            success = self.loop.run_until_complete(
                self._take_screenshot_async(temp_path)
            )
            
            if success and temp_path.exists():
                image = Image.open(temp_path)
                temp_path.unlink()  # Clean up temp file
                
                # Add timestamp overlay if debug mode is enabled
                if self.settings.debug_mode:
                    image = self._add_timestamp_overlay(image)
                
                return image
            else:
                self.logger.error("Failed to take persistent screenshot")
                return None
                
        except Exception as e:
            self.logger.error(f"Error taking persistent screenshot: {e}")
            return None
    
    def _add_timestamp_overlay(self, image: Image.Image) -> Image.Image:
        """Add a timestamp overlay to the bottom right corner of the image when debug mode is enabled.
        
        Args:
            image: PIL Image to add timestamp to
            
        Returns:
            PIL Image with timestamp overlay added
        """
        try:
            # Create a copy of the image to avoid modifying the original
            img_with_overlay = image.copy()
            draw = ImageDraw.Draw(img_with_overlay)
            
            # Get current timestamp
            now = datetime.now()
            timestamp_text = now.strftime("%Y-%m-%d %H:%M:%S")
            
            # Try to load a font, fall back to default if not available
            try:
                # Try to use a system font - adjust size based on display dimensions
                font_size = max(12, min(24, self.settings.display_width // 80))  # Scale font with display size
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
            except (OSError, IOError):
                try:
                    # Fall back to default PIL font
                    font = ImageFont.load_default()
                except:
                    # If all else fails, use None (PIL will use built-in font)
                    font = None
            
            # Calculate text dimensions
            if font:
                bbox = draw.textbbox((0, 0), timestamp_text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                # Estimate dimensions for default font
                text_width = len(timestamp_text) * 6
                text_height = 11
            
            # Calculate position for bottom right corner
            buffer_pixels = 50
            x = self.settings.display_width - text_width - buffer_pixels
            y = self.settings.display_height - text_height - buffer_pixels
            
            # Ensure position is not negative
            x = max(0, x)
            y = max(0, y)
            
            # Draw a semi-transparent background rectangle for better readability
            padding = 4
            bg_x1 = x - padding
            bg_y1 = y - padding
            bg_x2 = x + text_width + padding
            bg_y2 = y + text_height + padding
            
            # Draw white background with slight transparency effect (using a solid color for e-ink)
            draw.rectangle([bg_x1, bg_y1, bg_x2, bg_y2], fill=(255, 255, 255), outline=(0, 0, 0), width=1)
            
            # Draw the timestamp text in black
            draw.text((x, y), timestamp_text, fill=(0, 0, 0), font=font)
            
            return img_with_overlay
            
        except Exception as e:
            self.logger.error(f"Failed to add timestamp overlay: {e}")
            # Return original image if overlay fails
            return image

    async def _take_screenshot_async(self, output_path: Path) -> bool:
        """Async method to take screenshot."""
        try:
            start_time = time.time()
            await self.page.screenshot(path=str(output_path), full_page=True)
            duration = time.time() - start_time
            self.logger.info(f"Persistent screenshot taken in {duration:.1f}s")
            return True
        except Exception as e:
            self.logger.error(f"Failed to take async screenshot: {e}")
            return False
    
    def refresh_persistent_browser(self) -> bool:
        """Refresh the persistent browser page."""
        if not self.is_persistent_browser_running or not self.loop:
            return False
        
        try:
            return self.loop.run_until_complete(self._refresh_page_async())
        except Exception as e:
            self.logger.error(f"Failed to refresh persistent browser: {e}")
            return False
    
    async def _refresh_page_async(self) -> bool:
        """Async method to refresh page."""
        try:
            self.logger.info("Refreshing persistent browser page...")
            await self.page.reload(wait_until="networkidle")
            await self._optimize_page_for_eink()
            return True
        except Exception as e:
            self.logger.error(f"Failed to refresh page: {e}")
            return False
    
    def cleanup_persistent_browser(self):
        """Clean up persistent browser resources."""
        if self.loop:
            try:
                self.loop.run_until_complete(self._cleanup_persistent_browser())
                self.loop.close()
                self.loop = None
            except Exception as e:
                self.logger.error(f"Error during persistent browser cleanup: {e}")
    
    async def _cleanup_persistent_browser(self):
        """Async method to clean up browser resources."""
        self.is_persistent_browser_running = False
        
        try:
            if self.context:
                await self.context.close()
                self.context = None
                
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
                
            self.page = None
            self.current_url = None
            
            self.logger.info("Persistent browser cleaned up")
            
        except Exception as e:
            self.logger.error(f"Error during async cleanup: {e}")
