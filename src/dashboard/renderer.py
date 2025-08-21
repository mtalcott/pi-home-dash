"""
Dashboard renderer for Pi Home Dashboard.
Handles rendering of dashboard content using headless browser or custom layouts.
"""

import asyncio
import logging
import subprocess
import tempfile
import time
from pathlib import Path
from PIL import Image
from typing import Optional

from playwright.async_api import async_playwright, BrowserContext, Page


class DashboardRenderer:
    """Main dashboard rendering class."""
    
    def __init__(self, settings):
        """Initialize the dashboard renderer."""
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.browser_bin = "chromium"
        
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
            if self.settings.dashboard_type == "dakboard":
                return self._render_dakboard()
            elif self.settings.dashboard_type == "custom":
                return self._render_custom()
            elif self.settings.dashboard_type == "integration_test":
                return self._render_integration_test()
            else:
                raise ValueError(f"Unknown dashboard type: {self.settings.dashboard_type}")
                
        except Exception as e:
            self.logger.error(f"Error rendering dashboard: {e}")
            return None
    
    def _render_dakboard(self):
        """Render DAKboard using headless browser."""
        if not self.settings.dakboard_url:
            self.logger.error("DAKboard URL not configured")
            return None

        self.logger.info(f"Rendering DAKboard from URL: {self.settings.dakboard_url}")
        return self._run_chromium(self.settings.dakboard_url, self.settings.browser_timeout)
    
    def _render_integration_test(self):
        """Render integration test dashboard using local HTML file."""
        self.logger.info("Rendering integration test dashboard")

        if not hasattr(self.settings, 'test_html_path') or self.settings.test_html_path is None:
            self.logger.error("Integration test HTML path not configured")
            return None

        if not self.settings.test_html_path.exists():
            self.logger.error(f"Integration test HTML file not found: {self.settings.test_html_path}")
            return None

        file_url = f"file://{self.settings.test_html_path.absolute()}"
        self.logger.info(f"Rendering integration test from: {file_url}")

        # Use a shorter timeout for tests
        timeout = min(self.settings.browser_timeout, 15)
        return self._run_chromium(file_url, timeout)
    
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
                return image
            else:
                self.logger.error("Failed to take persistent screenshot")
                return None
                
        except Exception as e:
            self.logger.error(f"Error taking persistent screenshot: {e}")
            return None
    
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

    def _run_chromium(self, url, timeout):
        """Render a URL using headless Chromium and return a PIL Image."""
        try:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_path = temp_file.name

            # Use shared chrome_args and add specific screenshot arguments
            cmd = [self.browser_bin] + self.chrome_args + [
                '--virtual-time-budget=10000',
                f'--window-size={self.settings.browser_width},{self.settings.browser_height}',
                f'--screenshot={temp_path}',
                url
            ]

            self.logger.debug(f"Running command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode != 0:
                self.logger.error(f"Chromium failed: {result.stderr}")
                return None

            if Path(temp_path).exists():
                image = Image.open(temp_path)
                Path(temp_path).unlink()
                self.logger.info(f"Successfully rendered {url}")
                return image
            else:
                self.logger.error("Screenshot file not created")
                return None

        except subprocess.TimeoutExpired:
            self.logger.error(f"Browser rendering timed out for {url}")
            return None
        except Exception as e:
            self.logger.error(f"Error rendering URL {url}: {e}")
            return None
