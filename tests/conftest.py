import pytest
from playwright.sync_api import expect, Browser, BrowserContext, Page
import json
import os
from pages.chat_page import ChatPage
from loguru import logger

# Load configuration
with open("config/config.json") as f:
    config = json.load(f)

# Load test data
with open("data/test-data.json") as f:
    test_data = json.load(f)

def pytest_addoption(parser):
    """Add command line options for language selection"""
    parser.addoption(
        "--language",
        action="store",
        default="en",
        help="Language to run tests in (en/ar)"
    )

@pytest.fixture(scope="session")
def language(request):
    """Get language from command line option"""
    return request.config.getoption("--language")

@pytest.fixture(scope="session")
def browser_context_args():
    """Set browser context arguments for all tests"""
    return {
        "viewport": {"width": 1280, "height": 800},
        "ignore_https_errors": True
    }

@pytest.fixture(scope="session")
def context(browser, language) -> BrowserContext:
    """Create a persistent browser context"""
    # Set up locale and timezone
    context = browser.new_context(
        locale=language,
        timezone_id="UTC",
        viewport={"width": config["viewport_sizes"]["desktop"]["width"], 
                 "height": config["viewport_sizes"]["desktop"]["height"]},
        base_url=config["base_url"]
    )
    
    # Add script to set RTL direction for Arabic
    if language == "ar":
        context.add_init_script("""
            Object.defineProperty(document.documentElement, 'dir', {
                get: () => 'rtl',
                set: () => {}
            });
            Object.defineProperty(document.documentElement, 'lang', {
                get: () => 'ar',
                set: () => {}
            });
        """)
    
    yield context
    context.close()

@pytest.fixture(scope="session")
def auth_page(context: BrowserContext, language) -> Page:
    """Create a persistent page for authentication"""
    page = context.new_page()
    
    # Navigate to page
    page.goto(config["base_url"])
    
    # Wait for page to load
    page.wait_for_load_state('domcontentloaded')
    
    # Initialize chat page
    chat_page = ChatPage(page)
    
    # Perform login
    assert chat_page.login(
        config["auth"]["email"],
        config["auth"]["password"]
    ), "Login failed"
    
    # Wait for successful login
    assert chat_page.wait_for_selector(chat_page.input_selector), "Chat input not found after login"
    
    yield page
    page.close()

@pytest.fixture(scope="function")
def test_page(context: BrowserContext, request) -> Page:
    """Create a new page in the authenticated context for each test"""
    try:
        # Get viewport size from test parameters if available
        viewport_size = getattr(request, "param", "desktop")
        viewport = config["viewport_sizes"].get(viewport_size, {"width": 1280, "height": 800})
        
        # Create new page in same context
        page = context.new_page()
        logger.info(f"Created new page with viewport: {viewport}")
        
        # Set viewport
        page.set_viewport_size(viewport)
        logger.info("Viewport size set")
        
        # Navigate to page
        page.goto(config["base_url"])
        logger.info(f"Navigated to {config['base_url']}")
        
        # Wait for page to be fully loaded
        page.wait_for_load_state('domcontentloaded')
        page.wait_for_load_state('networkidle')
        logger.info("Page fully loaded")
        
        # Initialize chat page
        chat_page = ChatPage(page)
        logger.info("Chat page initialized")
        
        # Step 1: Wait for email input and fill
        logger.info("Waiting for email input...")
        page.wait_for_selector(chat_page.email_input_selector, timeout=10000)
        page.fill(chat_page.email_input_selector, config["auth"]["email"])
        logger.info("Email filled")
        
        # Step 2: Wait for password input and fill
        logger.info("Waiting for password input...")
        page.wait_for_selector(chat_page.password_input_selector, timeout=10000)
        page.fill(chat_page.password_input_selector, config["auth"]["password"])
        logger.info("Password filled")
        
        # Step 3: Wait for login button and click
        logger.info("Waiting for login button...")
        page.wait_for_selector(chat_page.login_button_selector, timeout=10000)
        # Ensure button is enabled
        expect(page.locator(chat_page.login_button_selector)).to_be_enabled()
        page.click(chat_page.login_button_selector)
        logger.info("Login button clicked")
        
        # Step 4: Wait for navigation
        logger.info("Waiting for navigation to complete...")
        page.wait_for_load_state('networkidle')
        logger.info("Navigation completed")
        
        # Step 5: Verify login success
        logger.info("Verifying login success...")
        assert page.url.endswith("/"), "Not on home page after login"
        logger.info("URL verification passed")
        
        # Step 6: Wait for chat input with retry
        logger.info("Waiting for chat input...")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                page.wait_for_selector(chat_page.input_selector, timeout=10000)
                logger.info("Chat input found - Login successful")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Chat input not found after {max_retries} attempts")
                    raise
                logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                page.reload()
                page.wait_for_load_state('networkidle')
        
        yield page
        
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        # Take screenshot on failure
        if 'page' in locals():
            page.screenshot(path=f"reports/screenshots/login_error_{viewport_size}.png")
        raise
    finally:
        if 'page' in locals():
            page.close()
            logger.info("Test page closed") 