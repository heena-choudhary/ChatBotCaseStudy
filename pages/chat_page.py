from .base_page import BasePage
from playwright.sync_api import Page, expect
import time

class ChatPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        # Login selectors
        self.email_input_selector = "//input[@type='email']"
        self.password_input_selector = "//input[@type='password']"
        self.login_button_selector = "button[type='submit']"
        # Chat selectors
        self.input_selector = "//*[@id='chat-input']"
        self.send_button_selector = "//button[@id='send-message-button']"
        self.message_selector = "//*[@id='response-content-container']/div[1]/p"
        self.last_message_selector = "(//p[@dir='auto'])[last()]"
        self.loading_indicator_selector = "//*[@id='loading-indicator']"
        self.response_container_selector = "//*[@id='response-content-container']"

    def login(self, email: str, password: str):
        """Login to the application"""
        try:
            self.logger.info("Attempting to login")
            # Wait for email input and fill
            self.wait_for_selector(self.email_input_selector)
            self.fill(self.email_input_selector, email)
            
            # Wait for password input and fill
            self.wait_for_selector(self.password_input_selector)
            self.fill(self.password_input_selector, password)
            
            # Wait for login button to be enabled
            self.wait_for_selector(self.login_button_selector)
            self.click(self.login_button_selector)
            
            # Wait for navigation after login
            self.page.wait_for_load_state('networkidle')
            
            # Wait for chat input to be visible
            self.wait_for_selector(self.input_selector)
            self.logger.info("Login successful")
            return True
        except Exception as e:
            self.logger.error(f"Login failed: {str(e)}")
            return False

    def login_mobile(self, email: str, password: str):
        """Login to the application in mobile view"""
        try:
            self.logger.info("Attempting mobile login")
            
            # Wait for mobile menu button and click it
            mobile_menu_selector = "button[aria-label='Menu']"
            self.wait_for_selector(mobile_menu_selector)
            self.click(mobile_menu_selector)
            
            # Wait for login link in mobile menu and click it
            mobile_login_selector = "a[href*='login']"
            self.wait_for_selector(mobile_login_selector)
            self.click(mobile_login_selector)
            
            # Wait for email input and fill
            self.wait_for_selector(self.email_input_selector)
            self.fill(self.email_input_selector, email)
            
            # Wait for password input and fill
            self.wait_for_selector(self.password_input_selector)
            self.fill(self.password_input_selector, password)
            
            # Wait for login button to be enabled
            self.wait_for_selector(self.login_button_selector)
            self.click(self.login_button_selector)
            
            # Wait for navigation after login
            self.page.wait_for_load_state('networkidle')
            
            # Wait for chat input to be visible
            self.wait_for_selector(self.input_selector)
            self.logger.info("Mobile login successful")
            return True
        except Exception as e:
            self.logger.error(f"Mobile login failed: {str(e)}")
            return False

    def load_chat_widget(self):
        """Wait for chat widget to load"""
        try:
            # Wait for page to be fully loaded
            self.page.wait_for_load_state('domcontentloaded')
            self.page.wait_for_load_state('networkidle')
            
            # Wait for chat input to be visible and enabled
            self.wait_for_selector(self.input_selector)
            expect(self.page.locator(self.input_selector)).to_be_enabled()
            
            # Additional wait for any animations
            time.sleep(3)
            
            self.logger.info("Chat widget loaded successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load chat widget: {str(e)}")
            return False

    def send_message(self, message: str):
        """Send a message and wait for response"""
        try:
            # Get current message count
            initial_messages = self.page.locator(self.message_selector).count()
            
            # Wait for input to be ready
            self.wait_for_selector(self.input_selector)
            input_element = self.page.locator(self.input_selector)
            expect(input_element).to_be_enabled()
            
            # Clear any existing text and fill new message
            input_element.fill("")
            input_element.type(message, delay=100)  # Add small delay between keystrokes
            
            # Wait for send button and ensure it's clickable
            self.wait_for_selector(self.send_button_selector)
            send_button = self.page.locator(self.send_button_selector)
            expect(send_button).to_be_enabled()
            
            # Close the overlay using the specified locator
            overlay_locator = '//a[@href="https://github.com/open-webui/open-webui/releases"]//parent::div/following-sibling::div/button'
            try:
                overlay = self.page.locator(overlay_locator)
                if overlay.is_visible():
                    overlay.click()
            except Exception as e:
                self.logger.warning(f"Failed to close overlay: {str(e)}")
            
            # Click send button with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    send_button.click()
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    # Wait a bit before retrying
                    self.page.wait_for_timeout(1000)
            
            # Wait for message to appear in chat
            try:
                self.page.wait_for_function(
                    f"document.querySelectorAll('{self.message_selector}').length > {initial_messages}",
                    timeout=5000
                )
            except:
                self.logger.warning("Message count did not increase")
            
            # Wait for network activity to settle
            self.page.wait_for_load_state('networkidle')
            
            self.logger.info(f"Sent message: {message}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send message: {str(e)}")
            return False

    def wait_for_response(self, timeout: int = 30000, stability_time: int = 2):
        """Wait for AI response with improved stability checks"""
        try:
            # Get current message count
            initial_messages = self.page.locator(self.message_selector).count()
            initial_time = time.time()
            
            # Wait for loading indicator to appear
            try:
                self.wait_for_selector(self.loading_indicator_selector, timeout=5000)
                self.logger.info("Loading indicator appeared")
            except:
                self.logger.warning("Loading indicator not found")
            
            # Wait for new message to appear
            while time.time() - initial_time < timeout/1000:
                current_messages = self.page.locator(self.message_selector).count()
                if current_messages > initial_messages:
                    # Wait for loading indicator to disappear
                    try:
                        self.page.wait_for_selector(self.loading_indicator_selector, state="hidden", timeout=5000)
                    except:
                        pass
                    
                    # Wait for network idle with retry
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            self.page.wait_for_load_state('networkidle', timeout=10000)
                            break
                        except:
                            if attempt == max_retries - 1:
                                self.logger.warning("Network did not become idle")
                    
                    # Get initial response
                    initial_response = self.get_complete_response()
                    if not initial_response:
                        continue
                        
                    # Wait for stability
                    time.sleep(stability_time)
                    final_response = self.get_complete_response()
                    
                    if initial_response == final_response and final_response.strip():
                        self.logger.info("Response received and stable")
                        return True
                time.sleep(0.5)
            
            self.logger.error("Timeout waiting for response")
            return False
        except Exception as e:
            self.logger.error(f"Failed to get response: {str(e)}")
            return False

    def get_complete_response(self) -> str:
        """Get the complete response including all paragraphs"""
        try:
            # Wait for response container
            self.wait_for_selector(self.response_container_selector)
            
            # Get all paragraphs
            paragraphs = self.page.locator(self.message_selector).all()
            
            # Extract text from each paragraph
            response_parts = []
            for paragraph in paragraphs:
                text = paragraph.text_content().strip()
                if text:
                    response_parts.append(text)
            
            return "\n".join(response_parts)
        except Exception as e:
            self.logger.error(f"Failed to get complete response: {str(e)}")
            return ""

    def get_last_message(self) -> str:
        """Get only the last message text"""
        try:
            # Wait for response container
            self.wait_for_selector(self.response_container_selector)
            
            # Get the last message paragraph
            last_message = self.page.locator(self.last_message_selector).last
            if last_message:
                return last_message.text_content().strip()
            return ""
        except Exception as e:
            self.logger.error(f"Failed to get last message: {str(e)}")
            return ""

    def validate_response(self, min_words: int = 10, max_words: int = 1000) -> dict:
        """Validate response content and structure"""
        try:
            response = self.get_complete_response()
            paragraphs = response.split("\n")
            
            validation = {
                "is_valid": True,
                "errors": [],
                "warnings": [],
                "metrics": {
                    "word_count": len(response.split()),
                    "char_count": len(response),
                    "paragraph_count": len(paragraphs)
                }
            }
            
            # Check word count
            if validation["metrics"]["word_count"] < min_words:
                validation["is_valid"] = False
                validation["errors"].append(f"Response too short: {validation['metrics']['word_count']} words")
            elif validation["metrics"]["word_count"] > max_words:
                validation["warnings"].append(f"Response very long: {validation['metrics']['word_count']} words")
            
            # Check paragraph structure
            if not paragraphs:
                validation["is_valid"] = False
                validation["errors"].append("No paragraphs found in response")
            
            # Check for empty paragraphs
            empty_paragraphs = [i for i, p in enumerate(paragraphs) if not p.strip()]
            if empty_paragraphs:
                validation["warnings"].append(f"Empty paragraphs found at positions: {empty_paragraphs}")
            
            return validation
        except Exception as e:
            self.logger.error(f"Failed to validate response: {str(e)}")
            return {
                "is_valid": False,
                "errors": [f"Validation failed: {str(e)}"],
                "warnings": [],
                "metrics": {}
            }

    def check_scroll_behavior(self):
        """Check if chat area scrolls properly"""
        try:
            # Wait for page to be stable
            self.page.wait_for_load_state('networkidle')
            
            # Scroll to bottom
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            # Wait for scroll animation
            time.sleep(0.5)
            
            # Wait for last message and check visibility
            self.wait_for_selector(self.last_message_selector)
            return self.page.is_visible(self.last_message_selector)
        except Exception as e:
            self.logger.error(f"Scroll check failed: {str(e)}")
            return False 