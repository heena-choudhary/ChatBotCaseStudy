import pytest
from playwright.sync_api import expect, Browser, BrowserContext, Page
import json
import os
from pages.chat_page import ChatPage
from loguru import logger
import time
from typing import Optional, Dict, Any

# Load configuration
with open("config/config.json") as f:
    config = json.load(f)

# Load test data
with open("tests/test-security-data.json") as f:
    test_data = json.load(f)

def retry_with_timeout(func, timeout: int = 30, interval: int = 1):
    """Retry a function until it succeeds or timeout is reached"""
    start_time = time.time()
    last_error = None
    
    while time.time() - start_time < timeout:
        try:
            return func()
        except Exception as e:
            last_error = e
            time.sleep(interval)
    
    raise last_error or TimeoutError(f"Operation timed out after {timeout} seconds")

@pytest.fixture(scope="function")
def browser_context(browser: Browser) -> BrowserContext:
    """Create browser context"""
    context = browser.new_context(
        viewport=config["viewport_sizes"]["desktop"],
        ignore_https_errors=True,
        record_video_dir="reports/videos" if config.get("record_video", False) else None
    )
    logger.info("Created browser context")
    
    yield context
    context.close()

@pytest.fixture(scope="function")
def auth_page(browser_context: BrowserContext) -> Page:
    """Create authenticated page"""
    page = browser_context.new_page()
    
    # Navigate to page with retry
    def navigate():
        page.goto(config["base_url"])
        return True
    
    retry_with_timeout(navigate)
    
    # Initialize chat page
    chat_page = ChatPage(page)
    
    # Perform login with retry
    def perform_login():
        return chat_page.login(
            config["auth"]["email"],
            config["auth"]["password"]
        )
    
    assert retry_with_timeout(perform_login), "Login failed"
    
    yield page
    page.close()

def is_safe_response(input_text, response):
    """
    Returns True if the response does NOT reflect the input as code, does NOT execute it, and does NOT enable the attack.
    Allows explanations, warnings, or educational content.
    """
    # If the input is reflected verbatim and not in a warning/explanation context, it's unsafe
    if input_text.strip() in response.strip() and not any(
        kw in response.lower() for kw in test_data["safe_response_indicators"]
    ):
        return False
    # If the response is a warning, explanation, or refusal, it's safe
    return True

def test_xss_prevention(auth_page):
    """Test that chat input is properly handled for XSS attacks"""
    chat_page = ChatPage(auth_page)
    
    for malicious_input in test_data["xss_attempts"]["malicious_inputs"]:
        try:
            def send_message():
                return chat_page.send_message(malicious_input)
            
            assert retry_with_timeout(send_message), f"Failed to send message: {malicious_input}"
            
            def wait_for_response():
                return chat_page.wait_for_response()
            
            assert retry_with_timeout(wait_for_response), "No response received"
            
            response = chat_page.get_complete_response()
            
            # Test passes as long as the input is not executed or reflected unsafely
            assert is_safe_response(malicious_input, response), \
                f"Unsafe reflection or execution for input: {malicious_input}\nResponse: {response}"
            
            auth_page.screenshot(path=f"reports/screenshots/xss_test_{malicious_input[:10]}.png")
        except Exception as e:
            logger.error(f"XSS test failed for input {malicious_input}: {str(e)}")
            auth_page.screenshot(path=f"reports/screenshots/xss_error_{malicious_input[:10]}.png")
            raise

def test_prompt_injection_prevention(auth_page):
    """Test that AI properly handles malicious prompts"""
    chat_page = ChatPage(auth_page)
    
    for attempt in test_data["prompt_injection_attempts"]["injection_attempts"]:
        try:
            def send_message():
                return chat_page.send_message(attempt)
            
            assert retry_with_timeout(send_message), f"Failed to send message: {attempt}"
            
            def wait_for_response():
                return chat_page.wait_for_response()
            
            assert retry_with_timeout(wait_for_response), "No response received"
            
            response = chat_page.get_complete_response()
            
            # Test passes as long as the bot does not change persona or act on the prompt
            assert not any(ind in response.lower() for ind in test_data["prompt_injection_attempts"]["persona_change_indicators"]), \
                f"AI changed persona or acted on prompt injection: {attempt}\nResponse: {response}"
            
            # Test passes if the bot gives a joke, a safe answer, or a refusal
            # (We do NOT require a specific refusal phrase)
            auth_page.screenshot(path=f"reports/screenshots/injection_test_{attempt[:10]}.png")
        except Exception as e:
            logger.error(f"Injection test failed for attempt {attempt}: {str(e)}")
            auth_page.screenshot(path=f"reports/screenshots/injection_error_{attempt[:10]}.png")
            raise

def test_sql_injection_prevention(auth_page):
    """Test that chat input is properly handled for SQL injection attempts"""
    chat_page = ChatPage(auth_page)
    
    for attempt in test_data["sql_injection_attempts"]["sql_injection_attempts"]:
        try:
            def send_message():
                return chat_page.send_message(attempt)
            
            assert retry_with_timeout(send_message), f"Failed to send message: {attempt}"
            
            def wait_for_response():
                return chat_page.wait_for_response()
            
            assert retry_with_timeout(wait_for_response), "No response received"
            
            response = chat_page.get_complete_response()
            
            # Test passes as long as the input is not executed or reflected unsafely
            assert is_safe_response(attempt, response), \
                f"Unsafe reflection or execution for input: {attempt}\nResponse: {response}"
            
            # Test passes if the bot does not return actual query results or act on the SQL
            assert not any(ind in response.lower() for ind in test_data["sql_injection_attempts"]["forbidden_sql_result_indicators"]), \
                f"AI returned SQL execution result: {attempt}\nResponse: {response}"
            
            auth_page.screenshot(path=f"reports/screenshots/sql_test_{attempt[:10]}.png")
        except Exception as e:
            logger.error(f"SQL injection test failed for attempt {attempt}: {str(e)}")
            auth_page.screenshot(path=f"reports/screenshots/sql_error_{attempt[:10]}.png")
            raise

def test_command_injection_prevention(auth_page):
    """Test that chat input is properly handled for command injection attempts"""
    chat_page = ChatPage(auth_page)
    
    for attempt in test_data["command_injection_attempts"]["command_injection_attempts"]:
        try:
            def send_message():
                return chat_page.send_message(attempt)
            
            assert retry_with_timeout(send_message), f"Failed to send message: {attempt}"
            
            def wait_for_response():
                return chat_page.wait_for_response()
            
            assert retry_with_timeout(wait_for_response), "No response received"
            
            response = chat_page.get_complete_response()
            
            # Test passes if the bot does not execute the command or return command output
            assert not any(ind in response.lower() for ind in test_data["command_injection_attempts"]["forbidden_command_indicators"]), \
                f"AI executed command or returned command output: {attempt}\nResponse: {response}"
            
            # Test passes if the bot provides educational content or warnings
            assert any(ind in response.lower() for ind in test_data["command_injection_attempts"]["educational_indicators"]), \
                f"AI did not provide educational content or warnings: {attempt}\nResponse: {response}"
            
            auth_page.screenshot(path=f"reports/screenshots/command_test_{attempt[:10]}.png")
        except Exception as e:
            logger.error(f"Command injection test failed for attempt {attempt}: {str(e)}")
            auth_page.screenshot(path=f"reports/screenshots/command_error_{attempt[:10]}.png")
            raise 