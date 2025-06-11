from playwright.sync_api import Page
from loguru import logger

class BasePage:
    def __init__(self, page: Page):
        self.page = page
        self.logger = logger

    def wait_for_selector(self, selector: str, timeout: int = 30000):
        """Wait for element to be present and visible"""
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception as e:
            self.logger.error(f"Element {selector} not found: {str(e)}")
            return False

    def click(self, selector: str):
        """Click element with logging"""
        try:
            self.page.click(selector)
            self.logger.info(f"Clicked element: {selector}")
        except Exception as e:
            self.logger.error(f"Failed to click {selector}: {str(e)}")
            raise

    def fill(self, selector: str, text: str):
        """Fill input with text"""
        try:
            self.page.fill(selector, text)
            self.logger.info(f"Filled {selector} with: {text}")
        except Exception as e:
            self.logger.error(f"Failed to fill {selector}: {str(e)}")
            raise

    def get_text(self, selector: str) -> str:
        """Get text content of element"""
        try:
            return self.page.text_content(selector)
        except Exception as e:
            self.logger.error(f"Failed to get text from {selector}: {str(e)}")
            raise 