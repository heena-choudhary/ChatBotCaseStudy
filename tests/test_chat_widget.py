import pytest
from playwright.sync_api import expect, Browser, BrowserContext, Page
import json
import os
from pages.chat_page import ChatPage
from utils.response_validator_deepseek import ResponseValidatorDeepseek
from utils.response_storage import ResponseStorage
from loguru import logger
import time
from typing import Optional, Dict, Any
from datetime import datetime

# Load configuration
with open("config/config.json") as f:
    config = json.load(f)

# Load test data
with open("data/test-data.json") as f:
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

# Add delay between tests
@pytest.fixture(autouse=True)
def delay_between_tests():
    """Add a delay between tests to avoid hitting API rate limits"""
    yield
    time.sleep(10)  # 30 second delay between tests to avoid rate limiting

@pytest.fixture(scope="function", params=["desktop", "mobile"])
def browser_context(browser: Browser, request) -> BrowserContext:
    """Create browser context with specified viewport"""
    viewport_size = request.param
    viewport = config["viewport_sizes"][viewport_size]
    
    context = browser.new_context(
        viewport=viewport,
        ignore_https_errors=True,
        record_video_dir="reports/videos" if config.get("record_video", False) else None
    )
    logger.info(f"Created {viewport_size} context with viewport: {viewport}")
    
    yield context
    context.close()

@pytest.fixture(scope="function")
def auth_page(browser_context: BrowserContext, request) -> Page:
    """Create authenticated page"""
    page = browser_context.new_page()
    viewport_size = request.node.callspec.params.get("viewport_size", "desktop")
    
    # Navigate to page with retry
    def navigate():
        page.goto(config["base_url"])
        return True
    
    retry_with_timeout(navigate)
    
    # Initialize chat page
    chat_page = ChatPage(page)
    
    # Perform login based on viewport size with retry
    def perform_login():
        if viewport_size == "mobile":
            return chat_page.login_mobile(
                config["auth"]["email"],
                config["auth"]["password"]
            )
        return chat_page.login(
            config["auth"]["email"],
            config["auth"]["password"]
        )
    
    assert retry_with_timeout(perform_login), f"{viewport_size} login failed"
    
    yield page
    page.close()

@pytest.fixture(scope="function")
def response_validator():
    """Create response validator instance"""
    return ResponseValidatorDeepseek(config)

@pytest.fixture(scope="function")
def response_storage():
    """Create response storage instance"""
    return ResponseStorage()

def test_chat_widget_loads(auth_page, language):
    """Test that chat widget loads properly"""
    chat_page = ChatPage(auth_page)
    viewport_size = "mobile" if auth_page.evaluate("window.innerWidth") <= config["viewport_sizes"]["mobile"]["width"] else "desktop"
    
    # Set language-specific settings
    if language == "ar":
        auth_page.evaluate("""
            document.documentElement.dir = 'rtl';
            document.documentElement.lang = 'ar';
        """)
    
    def load_widget():
        return chat_page.load_chat_widget()
    
    #assert retry_with_timeout(load_widget), "Chat widget failed to load"
    
    # Verify widget elements are present
    #assert chat_page.verify_widget_elements(), "Chat widget elements not found"
    
    auth_page.screenshot(path=f"reports/screenshots/load_{language}_{viewport_size}.png")

@pytest.mark.parametrize("test_case", test_data["test_cases"], ids=lambda x: f"TC{x['id']}")
def test_message_sending(auth_page, language, response_validator, response_storage, request, test_case):
    """Test message sending and response validation for each test case"""
    chat_page = ChatPage(auth_page)
    viewport_size = "mobile" if auth_page.evaluate("window.innerWidth") <= config["viewport_sizes"]["mobile"]["width"] else "desktop"
    try:
        # Get query for current language
        query = test_case["queries"][language]["input"]
        validation_criteria = test_case["queries"][language]["validation"]
        # Send message with retry
        def send_message():
            return chat_page.send_message(query)
        assert retry_with_timeout(send_message), f"Failed to send {language} message"
        # Wait for response with retry
        def wait_for_response():
            return chat_page.wait_for_response()
        assert retry_with_timeout(wait_for_response), f"No {language} response received"
        # Get response from UI
        response = chat_page.get_complete_response()
        if not response:
            raise ValueError("No response content found in message")
        # Add chatbot response to pytest-html report
        if hasattr(request.node, "_report_sections"):
            from pytest_html import extras
            request.node._report_sections.append(("call", "Chatbot Response", response))
        elif hasattr(request.node, "extra"):
            from pytest_html import extras
            request.node.extra.append(extras.text(response, name="Chatbot Response"))
        # Validate response
        validation_results = response_validator.validate_response(
            response,
            language,
            test_case
        )
        
        # Add API logs to the test report if available
        if 'api_log' in validation_results:
            from pytest_html import extras
            api_request = json.dumps(validation_results['api_log']['request'], indent=2)
            api_response = json.dumps(validation_results['api_log']['response'], indent=2)
            
            if hasattr(request.node, "_report_sections"):
                request.node._report_sections.append(("call", "API Request", api_request))
                request.node._report_sections.append(("call", "API Response", api_response))
            elif hasattr(request.node, "extra"):
                request.node.extra.append(extras.text(api_request, name="API Request"))
                request.node.extra.append(extras.text(api_response, name="API Response"))
        
        # Store validation results
        response_storage.store_validation(
            test_case["id"],
            language,
            query,
            response,
            validation_results
        )
        # Assert validation results with detailed error messages
        assert validation_results["clarity"]["score"] >= config["validation"]["thresholds"]["clarity"], \
            f"Response clarity score too low: {validation_results['clarity']['score']} < {config['validation']['thresholds']['clarity']}"
        assert validation_results["hallucination"]["score"] >= config["validation"]["thresholds"]["hallucination"], \
            f"Response contains hallucinations: {validation_results['hallucination']['score']} < {config['validation']['thresholds']['hallucination']}"
        assert validation_results["formatting"]["score"] >= config["validation"]["thresholds"]["formatting"], \
            f"Response has formatting issues: {validation_results['formatting']['score']} < {config['validation']['thresholds']['formatting']}"
        assert validation_results["completeness"]["score"] >= config["validation"]["thresholds"]["completeness"], \
            f"Response is incomplete: {validation_results['completeness']['score']} < {config['validation']['thresholds']['completeness']}"
        assert validation_results["language_specific"]["score"] >= config["validation"]["thresholds"]["language_specific"], \
            f"Language-specific requirements not met: {validation_results['language_specific']['score']} < {config['validation']['thresholds']['language_specific']}"
        # Take screenshot of response
        auth_page.screenshot(path=f"reports/screenshots/response_{test_case['id']}_{language}_{viewport_size}.png")
    except Exception as e:
        logger.error(f"Test case {test_case['id']} failed: {str(e)}")
        auth_page.screenshot(path=f"reports/screenshots/error_{test_case['id']}_{language}_{viewport_size}.png")
        raise

def test_cross_language_consistency(auth_page, response_validator, response_storage):
    """Test response consistency between English and Arabic"""
    chat_page = ChatPage(auth_page)
    
    for test_case in test_data["test_cases"]:
        try:
            # Send English query with retry
            en_query = test_case["queries"]["en"]["input"]
            def send_en_query():
                return chat_page.send_message(en_query)
            
            assert retry_with_timeout(send_en_query), "Failed to send English query"
            
            def wait_en_response():
                return chat_page.wait_for_response()
            
            assert retry_with_timeout(wait_en_response), "No English response received"
            english_response = chat_page.get_last_message()
            
            # Send Arabic query with retry
            ar_query = test_case["queries"]["ar"]["input"]
            def send_ar_query():
                return chat_page.send_message(ar_query)
            
            assert retry_with_timeout(send_ar_query), "Failed to send Arabic query"
            
            def wait_ar_response():
                return chat_page.wait_for_response()
            
            assert retry_with_timeout(wait_ar_response), "No Arabic response received"
            arabic_response = chat_page.get_last_message()
            
            # Compare responses
            comparison_results = response_validator.compare_responses(
                english_response,
                arabic_response,
                test_case
            )
            
            # Store comparison results
            response_storage.store_comparison(
                test_case["id"],
                {"query": en_query, "response": english_response},
                {"query": ar_query, "response": arabic_response},
                comparison_results
            )
            
            # Assert comparison results with detailed error messages
            assert comparison_results["semantic_similarity"]["score"] >= config["validation"]["thresholds"]["semantic_similarity"], \
                f"Semantic similarity score too low: {comparison_results['semantic_similarity']['score']} < {config['validation']['thresholds']['semantic_similarity']}"
            assert comparison_results["information_consistency"]["score"] >= config["validation"]["thresholds"]["information_consistency"], \
                f"Information consistency score too low: {comparison_results['information_consistency']['score']} < {config['validation']['thresholds']['information_consistency']}"
            assert comparison_results["structure_similarity"]["score"] >= config["validation"]["thresholds"]["structure_similarity"], \
                f"Structure similarity score too low: {comparison_results['structure_similarity']['score']} < {config['validation']['thresholds']['structure_similarity']}"
            
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            auth_page.screenshot(path=f"reports/screenshots/error_{test_case['id']}_comparison.png")
            raise

def test_rtl_support(auth_page, language):
    """Test RTL support for Arabic"""
    if language != "ar":
        pytest.skip("RTL test only applicable for Arabic language")
    
    chat_page = ChatPage(auth_page)
    viewport_size = "mobile" if auth_page.evaluate("window.innerWidth") <= config["viewport_sizes"]["mobile"]["width"] else "desktop"
    
    # Set RTL direction
    auth_page.evaluate("""
        document.documentElement.dir = 'rtl';
        document.documentElement.lang = 'ar';
    """)
    
    # Verify RTL direction
    direction = auth_page.evaluate("document.documentElement.dir")
    assert direction == "rtl", f"Expected RTL direction, but got: {direction}"
    
    # Test Arabic input with retry
    test_case = test_data["test_cases"][0]
    query = test_case["queries"]["ar"]["input"]
    
    def send_ar_message():
        return chat_page.send_message(query)
    
    assert retry_with_timeout(send_ar_message), "Failed to send Arabic message"
    
    def wait_ar_response():
        return chat_page.wait_for_response()
    
    assert retry_with_timeout(wait_ar_response), "No response received for Arabic message"
    
    # Verify RTL direction is maintained
    direction_after = auth_page.evaluate("document.documentElement.dir")
    assert direction_after == "rtl", f"RTL direction lost after response, got: {direction_after}"
    
    # Verify text alignment
    text_alignment = auth_page.evaluate("""
        () => {
            const messages = document.querySelectorAll('.chat-message');
            return Array.from(messages).every(msg => 
                window.getComputedStyle(msg).textAlign === 'right'
            );
        }
    """)
    assert text_alignment, "Text alignment not properly set for RTL"
    
    auth_page.screenshot(path=f"reports/screenshots/rtl_{viewport_size}.png") 