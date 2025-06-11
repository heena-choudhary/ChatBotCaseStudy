import os
import sys
import pytest
from playwright.sync_api import sync_playwright, Browser
from typing import Generator

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    """Create a browser instance for testing"""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)  # Run in headed mode
        yield browser
        browser.close()

@pytest.fixture(params=["en", "ar"])
def language(request) -> str:
    """Provide language parameter for tests"""
    return request.param 