"""
Browser Controller - Playwright-based browser automation
"""
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

from playwright.async_api import async_playwright, Browser, Page, BrowserContext

from ..config import settings


class BrowserController:
    """
    Playwright-based browser controller for game testing.
    Handles navigation, interactions, and state capture.
    """
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.console_logs: List[Dict] = []
        self.network_logs: List[Dict] = []
        
    async def start(self, headless: bool = None):
        """
        Start the browser.
        
        Args:
            headless: Run in headless mode. Defaults to settings.BROWSER_HEADLESS
        """
        if headless is None:
            headless = settings.BROWSER_HEADLESS
            
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=['--disable-web-security', '--disable-features=IsolateOrigins,site-per-process']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            record_video_dir=None  # Can enable for video recording
        )
        self.page = await self.context.new_page()
        
        # Set up console log capture
        self.page.on("console", self._handle_console)
        
        # Set up network log capture
        self.page.on("request", self._handle_request)
        self.page.on("response", self._handle_response)
        
        # Set timeout
        self.page.set_default_timeout(settings.BROWSER_TIMEOUT)
        
    async def stop(self):
        """Stop the browser and clean up resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            
    async def navigate(self, url: str, wait_until: str = "networkidle"):
        """
        Navigate to a URL.
        
        Args:
            url: The URL to navigate to
            wait_until: When to consider navigation succeeded
        """
        await self.page.goto(url, wait_until=wait_until)
        
    async def screenshot(self, path: str, full_page: bool = False) -> str:
        """
        Take a screenshot.
        
        Args:
            path: Path to save the screenshot
            full_page: Capture full page or just viewport
            
        Returns:
            Path to the saved screenshot
        """
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        await self.page.screenshot(path=path, full_page=full_page)
        return path
        
    async def click(self, selector: str, timeout: int = None):
        """
        Click an element.
        
        Args:
            selector: CSS selector or text for the element
            timeout: Custom timeout in ms
        """
        if timeout:
            await self.page.click(selector, timeout=timeout)
        else:
            await self.page.click(selector)
            
    async def click_at_position(self, x: int, y: int):
        """
        Click at specific coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
        """
        await self.page.mouse.click(x, y)
        
    async def type_text(self, selector: str, text: str):
        """
        Type text into an element.
        
        Args:
            selector: CSS selector for the input element
            text: Text to type
        """
        await self.page.fill(selector, text)
        
    async def press_key(self, key: str):
        """
        Press a keyboard key.
        
        Args:
            key: Key to press (e.g., 'Enter', 'Escape', 'ArrowUp')
        """
        await self.page.keyboard.press(key)
        
    async def wait_for_selector(self, selector: str, timeout: int = None) -> bool:
        """
        Wait for an element to appear.
        
        Args:
            selector: CSS selector to wait for
            timeout: Custom timeout in ms
            
        Returns:
            True if element found, False otherwise
        """
        try:
            if timeout:
                await self.page.wait_for_selector(selector, timeout=timeout)
            else:
                await self.page.wait_for_selector(selector)
            return True
        except:
            return False
            
    async def wait_for_timeout(self, ms: int):
        """
        Wait for a specific amount of time.
        
        Args:
            ms: Milliseconds to wait
        """
        await self.page.wait_for_timeout(ms)
        
    async def get_dom(self) -> str:
        """
        Get the current DOM as HTML.
        
        Returns:
            Full page HTML
        """
        return await self.page.content()
        
    async def get_element_text(self, selector: str) -> Optional[str]:
        """
        Get text content of an element.
        
        Args:
            selector: CSS selector for the element
            
        Returns:
            Text content or None if not found
        """
        try:
            element = await self.page.query_selector(selector)
            if element:
                return await element.text_content()
        except:
            pass
        return None
        
    async def get_element_attribute(self, selector: str, attribute: str) -> Optional[str]:
        """
        Get an attribute value from an element.
        
        Args:
            selector: CSS selector for the element
            attribute: Attribute name
            
        Returns:
            Attribute value or None if not found
        """
        try:
            element = await self.page.query_selector(selector)
            if element:
                return await element.get_attribute(attribute)
        except:
            pass
        return None
        
    async def get_all_elements(self, selector: str) -> List[Dict]:
        """
        Get information about all matching elements.
        
        Args:
            selector: CSS selector
            
        Returns:
            List of element info dictionaries
        """
        elements = []
        try:
            handles = await self.page.query_selector_all(selector)
            for i, handle in enumerate(handles):
                box = await handle.bounding_box()
                text = await handle.text_content()
                tag = await handle.evaluate("el => el.tagName.toLowerCase()")
                elements.append({
                    "index": i,
                    "tag": tag,
                    "text": text.strip() if text else "",
                    "box": box
                })
        except:
            pass
        return elements
        
    async def evaluate_js(self, script: str) -> Any:
        """
        Execute JavaScript in the page context.
        
        Args:
            script: JavaScript code to execute
            
        Returns:
            Result of the script execution
        """
        return await self.page.evaluate(script)
        
    async def get_game_state(self) -> Dict[str, Any]:
        """
        Extract current game state from the page.
        Looks for common game elements like scores, timers, etc.
        
        Returns:
            Dictionary with game state information
        """
        state = {}
        
        # Try to find score elements
        score_selectors = ['[class*="score"]', '[id*="score"]', '.score', '#score']
        for selector in score_selectors:
            text = await self.get_element_text(selector)
            if text:
                state['score'] = text.strip()
                break
                
        # Try to find any visible text elements that might be game controls
        state['visible_text'] = await self.evaluate_js("""
            () => {
                const texts = [];
                document.querySelectorAll('button, [role="button"], .btn, a').forEach(el => {
                    const text = el.textContent?.trim();
                    if (text && text.length < 50) {
                        texts.push(text);
                    }
                });
                return texts.slice(0, 20);
            }
        """)
        
        return state
        
    async def find_interactive_elements(self) -> List[Dict]:
        """
        Find all interactive elements on the page.
        
        Returns:
            List of interactive element details
        """
        return await self.evaluate_js("""
            () => {
                const elements = [];
                const interactable = document.querySelectorAll(
                    'button, a, input, [onclick], [role="button"], [tabindex], canvas, .clickable, [class*="tile"], [class*="cell"], [class*="card"]'
                );
                
                interactable.forEach((el, i) => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        elements.push({
                            index: i,
                            tag: el.tagName.toLowerCase(),
                            id: el.id || null,
                            class: el.className || null,
                            text: el.textContent?.trim().slice(0, 100) || null,
                            x: rect.x + rect.width / 2,
                            y: rect.y + rect.height / 2,
                            width: rect.width,
                            height: rect.height
                        });
                    }
                });
                
                return elements.slice(0, 100);
            }
        """)
        
    def get_console_logs(self) -> List[Dict]:
        """Get captured console logs."""
        return self.console_logs.copy()
        
    def get_network_logs(self) -> List[Dict]:
        """Get captured network logs."""
        return self.network_logs.copy()
        
    def clear_logs(self):
        """Clear captured logs."""
        self.console_logs = []
        self.network_logs = []
        
    def _handle_console(self, message):
        """Handle console messages."""
        self.console_logs.append({
            "timestamp": datetime.now().isoformat(),
            "type": message.type,
            "text": message.text,
            "location": str(message.location)
        })
        
    def _handle_request(self, request):
        """Handle network requests."""
        self.network_logs.append({
            "timestamp": datetime.now().isoformat(),
            "type": "request",
            "url": request.url,
            "method": request.method,
            "resource_type": request.resource_type
        })
        
    def _handle_response(self, response):
        """Handle network responses."""
        self.network_logs.append({
            "timestamp": datetime.now().isoformat(),
            "type": "response",
            "url": response.url,
            "status": response.status
        })
