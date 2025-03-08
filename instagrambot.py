from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
from faker import Faker
import undetected_chromedriver as uc
import logging
import time
import random
import requests
import json
import re
from datetime import datetime
from pathlib import Path
import pyautogui
import sys
import warnings
warnings.filterwarnings("ignore")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('instagram_creator.log'),
        logging.StreamHandler()
    ]
)

class DropMailClient:
    def __init__(self):
        self.session = requests.Session()
        self.email = None
        self.session_id = None
        self.token = None
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        self.api_url = 'https://dropmail.me/api/graphql/web-test-2'

    def create_inbox(self):
        try:
            query = '''
            mutation {
                introduceSession {
                    id
                    expiresAt
                    addresses {
                        address
                    }
                }
            }
            '''
            
            response = self.session.post(self.api_url, headers=self.headers, json={'query': query})
            
            if response.status_code != 200:
                raise Exception(f"API error: {response.status_code}")

            data = response.json()
            if 'errors' in data:
                raise Exception(f"GraphQL errors: {data['errors']}")

            session_data = data.get('data', {}).get('introduceSession', {})
            self.session_id = session_data.get('id')
            self.email = session_data.get('addresses', [{}])[0].get('address')
            
            if not self.session_id or not self.email:
                raise Exception("Failed to get session ID or email address")

            logging.info(f"Created new email: {self.email}")
            return self.email
            
        except Exception as e:
            logging.error(f"Error creating inbox: {str(e)}")
            return None

    def wait_for_verification_code(self, timeout=300):
        try:
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                query = '''
                query($sessionId: ID!) {
                    session(id: $sessionId) {
                        id
                        addresses {
                            address
                        }
                        mails {
                            rawSize
                            fromAddr
                            toAddr
                            downloadUrl
                            text
                            headerSubject
                        }
                    }
                }
                '''
                
                variables = {'sessionId': self.session_id}
                response = self.session.post(self.api_url, headers=self.headers, json={'query': query, 'variables': variables})

                if response.status_code != 200:
                    logging.error(f"API error: {response.status_code}")
                    time.sleep(5)
                    continue

                data = response.json()
                
                if 'errors' in data:
                    logging.error(f"GraphQL errors: {data['errors']}")
                    time.sleep(5)
                    continue

                session_data = data.get('data', {}).get('session', {})
                mails = session_data.get('mails', [])
                
                logging.info(f"Checking mails. Found {len(mails)} messages")
                
                for mail in mails:
                    from_addr = mail.get('fromAddr', '').lower()
                    mail_text = mail.get('text', '')
                    subject = mail.get('headerSubject', '')
                    
                    logging.info(f"Checking mail from: {from_addr}")
                    logging.info(f"Subject: {subject}")
                    
                    if 'instagram' in from_addr or 'instagram' in subject.lower():
                        match = re.search(r'\b\d{6}\b', mail_text)
                        if match:
                            code = match.group(0)
                            logging.info(f"Found verification code: {code}")
                            return code
                
                logging.info("No verification code found, waiting 5 seconds...")
                time.sleep(5)
            
            logging.warning("Timeout waiting for verification code")
            return None
            
        except Exception as e:
            logging.error(f"Error getting verification code: {str(e)}")
            return None

class BrowserStealth:
    """Browser stealth and anti-detection management"""
    @staticmethod
    def modify_navigator(driver):
        """Modify navigator properties"""
        navigator_modifications = {
            'webdriver': "undefined",
            'webdriver_status': False,
            'chrome_status': False,
            'driver_status': False,
            'webdriver_agent_status': False,
            'selenium_status': False,
            'domAutomation': False,
            'domAutomationController': False,
            'selenium': False,
            '_Selenium_IDE_Recorder': False,
            'calledSelenium': False,
            '_selenium': False,
            '__webdriver_script_fn': False
        }
        
        for key, value in navigator_modifications.items():
            driver.execute_script(f"Object.defineProperty(navigator, '{key}', {{get: () => {str(value).lower()}}});")

    @staticmethod
    def modify_window_properties(driver):
        """Modify window properties"""
        window_modifications = {
            'callPhantom': False,
            '_phantom': False,
            'phantom': False,
            'webdriver': False,
            '__nightmare': False
        }
        
        for key, value in window_modifications.items():
            driver.execute_script(f"Object.defineProperty(window, '{key}', {{get: () => {str(value).lower()}}});")

    @staticmethod
    def add_stealth_scripts(driver):
        """Add stealth scripts"""
        stealth_js = """
        try {
            // Save original functions
            const originalNavigatorPrototype = navigator.__proto__;
            const originalNavigatorPermissionsQuery = window.navigator.permissions.query;
            
            // Create a new prototype without webdriver flag
            const newProto = Object.create(originalNavigatorPrototype);
            delete newProto.webdriver;
            
            // Apply the modified prototype
            Object.setPrototypeOf(navigator, newProto);
            
            // Override permissions query
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({state: Notification.permission}) :
                originalNavigatorPermissionsQuery.call(window.navigator.permissions, parameters)
            );
            
            // Additional evasion techniques
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['tr-TR', 'tr', 'en-US', 'en']});
            
        } catch (err) {
            console.log('Stealth script error:', err);
        }
        """
        driver.execute_script(stealth_js)

    @staticmethod
    def add_mock_elements(driver):
        """Add mock DOM elements"""
        mock_elements = [
            ("div", {"id": "selenium-ide-indicator", "style": "display:none"}),
            ("div", {"id": "webdriver-indicator", "style": "display:none"}),
            ("div", {"id": "selenium-indicator", "style": "display:none"})
        ]
        for tag, attrs in mock_elements:
            attrs_str = ' '.join([f'{k}="{v}"' for k, v in attrs.items()])
            driver.execute_script(f"document.body.insertAdjacentHTML('beforeend', '<{tag} {attrs_str}></{tag}>')")

class ProxyManager:
    def __init__(self):
        self.proxies = self.load_proxies()
        self.failed_proxies = set()
        
    def load_proxies(self):
        """Load proxy list from file"""
        try:
            with open('proxies.txt', 'r') as f:
                return [line.strip() for line in f if line.strip() and self.is_valid_proxy_format(line.strip())]
        except FileNotFoundError:
            logging.warning("proxies.txt file not found. Running without proxies.")
            return []
    
    def is_valid_proxy_format(self, proxy):
        """Check proxy format"""
        proxy_pattern = r'^(https?://)?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})$'
        if re.match(proxy_pattern, proxy):
            ip = re.match(proxy_pattern, proxy).group(2)
            port = re.match(proxy_pattern, proxy).group(3)
            ip_parts = ip.split('.')
            if all(0 <= int(part) <= 255 for part in ip_parts) and 0 < int(port) <= 65535:
                return True
        return False
            
    def get_random_proxy(self):
        """Select a random proxy"""
        available_proxies = [p for p in self.proxies if p not in self.failed_proxies]
        if not available_proxies:
            if self.proxies:
                logging.warning("All proxies have failed. Resetting failed proxies list.")
                self.failed_proxies.clear()
                available_proxies = self.proxies
            else:
                return None
                
        proxy = random.choice(available_proxies)
        return proxy
    
    def mark_proxy_as_failed(self, proxy):
        """Mark a proxy as failed"""
        if proxy:
            self.failed_proxies.add(proxy)
            logging.warning(f"Marked proxy as failed: {proxy}")

class InstagramBot:
    def __init__(self, use_proxy=True):
        self.fake = Faker('tr_TR')
        self.dropmail = DropMailClient()
        self.proxy_manager = ProxyManager()
        self.current_proxy = None
        
        tries = 3  # Maximum number of proxy attempts
        for attempt in range(tries):
            try:
                options = uc.ChromeOptions()
                
                # User agent settings
                ua = UserAgent()
                user_agent = ua.random
                options.add_argument(f'user-agent={user_agent}')
                
                # Language setting
                options.add_argument('--lang=tr-TR')
                
                # WebRTC handling
                options.add_argument('--disable-webrtc')
                
                # Proxy settings
                if use_proxy:
                    self.current_proxy = self.proxy_manager.get_random_proxy()
                    if self.current_proxy:
                        logging.info(f"Attempting to connect with proxy: {self.current_proxy}")
                        options.add_argument(f'--proxy-server={self.current_proxy}')
                
                # Profile and other settings
                profile_path = Path.home() / "instagram_bot_profile"
                options.add_argument(f'--user-data-dir={str(profile_path)}')
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_argument('--disable-features=IsolateOrigins,site-per-process')
                options.add_argument('--disable-site-isolation-trials')
                
                # Initialize undetected-chromedriver
                self.driver = uc.Chrome(options=options)
                
                # Test proxy connection
                if self.current_proxy:
                    self.test_proxy_connection()
                
                # If we get here, the proxy is working
                break
                
            except Exception as e:
                logging.error(f"Failed to initialize with proxy (attempt {attempt + 1}/{tries}): {str(e)}")
                if self.current_proxy:
                    self.proxy_manager.mark_proxy_as_failed(self.current_proxy)
                if attempt == tries - 1:  # Last attempt
                    raise Exception("Failed to initialize browser with any proxy")
                continue
            
        # Set up other properties
        self.setup_browser_properties()

    def initialize_chrome_with_timeout(self, options, timeout=30):
        """Initialize Chrome with timeout"""
        def _init_chrome():
            return uc.Chrome(options=options)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_init_chrome)
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                raise Exception("Chrome initialization timed out")

    def test_proxy_connection(self):
        """Test proxy connection by loading a test page"""
        try:
            self.driver.set_page_load_timeout(30)
            self.driver.get("https://www.google.com")
        except Exception as e:
            raise Exception(f"Proxy connection test failed: {str(e)}")

    def setup_browser_properties(self):
        """Set up browser properties after successful initialization"""
        # Window size
        screen_width = 1920
        screen_height = 1080
        window_width = random.randint(1024, screen_width)
        window_height = random.randint(768, screen_height)
        self.driver.set_window_size(window_width, window_height)
        
        # Wait and actions
        self.wait = WebDriverWait(self.driver, 20)
        self.actions = ActionChains(self.driver)
        
        # Anti-detection
        BrowserStealth.modify_navigator(self.driver)
        BrowserStealth.modify_window_properties(self.driver)
        BrowserStealth.add_stealth_scripts(self.driver)
        BrowserStealth.add_mock_elements(self.driver)

        # Clear cookies and cache
        self.driver.delete_all_cookies()

    def generate_user_data(self):
        """Generate random user data"""
        username = f"{self.fake.user_name()}_{random.randint(100,999)}".lower()
        password = f"Pass_{self.fake.password(length=10)}#1"
        full_name = self.fake.name()
        
        username = username.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
        full_name = full_name.replace('İ', 'I').replace('Ğ', 'G').replace('Ü', 'U').replace('Ş', 'S').replace('Ö', 'O').replace('Ç', 'C')
        
        return username, password, full_name

    def generate_birth_date(self):
        """Generate random birth date between 18-50 years old"""
        year = random.randint(1973, 2005)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        return year, month, day

    def random_sleep(self, min_time=1, max_time=3):
        """Random sleep"""
        time.sleep(random.uniform(min_time, max_time))

    def human_type(self, element, text):
        """Human-like typing behavior"""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))
        self.random_sleep()

    def move_mouse_randomly(self):
        """Move mouse randomly"""
        try:
            viewport_width = self.driver.execute_script("return window.innerWidth;")
            viewport_height = self.driver.execute_script("return window.innerHeight;")
            x = random.randint(0, viewport_width)
            y = random.randint(0, viewport_height)
            self.actions.move_by_offset(x, y).perform()
            self.random_sleep(0.2, 0.5)
        except:
            pass

    def handle_cookie_popup(self):
        """Handle cookie popup"""
        try:
            cookie_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Tümünü Kabul Et')]")
            self.move_mouse_randomly()
            cookie_button.click()
            self.random_sleep()
        except:
            pass

    def create_account(self):
        try:
            # Create email
            email = self.dropmail.create_inbox()
            if not email:
                raise Exception("Failed to create email inbox")

            # Generate user data
            username, password, full_name = self.generate_user_data()
            
            # Open Instagram
            self.driver.get("https://www.instagram.com")
            self.random_sleep(3, 5)
            
            # Handle cookie popup
            self.handle_cookie_popup()

            # Click sign up button
            signup_link = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Kaydol']")))
            self.move_mouse_randomly()
            signup_link.click()
            self.random_sleep(2, 4)

            # Fill in form fields
            email_input = self.wait.until(EC.presence_of_element_located((By.NAME, "emailOrPhone")))
            fullname_input = self.wait.until(EC.presence_of_element_located((By.NAME, "fullName")))
            username_input = self.wait.until(EC.presence_of_element_located((By.NAME, "username")))
            password_input = self.wait.until(EC.presence_of_element_located((By.NAME, "password")))

            self.move_mouse_randomly()
            self.human_type(email_input, email)
            
            self.move_mouse_randomly()
            self.human_type(fullname_input, full_name)
            
            self.move_mouse_randomly()
            self.human_type(username_input, username)
            
            self.move_mouse_randomly()
            self.human_type(password_input, password)

            self.random_sleep(1, 2)

            # Click sign up button
            submit_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
            self.move_mouse_randomly()
            submit_button.click()
            self.random_sleep(3, 5)

            # Birthdate selection
            year, month, day = self.generate_birth_date()
            
            # Select month
            month_select = self.wait.until(EC.presence_of_element_located((By.XPATH, "//select[@title='Ay:']")))
            self.move_mouse_randomly()
            month_select.click()
            self.random_sleep()
            month_option = self.wait.until(EC.presence_of_element_located((By.XPATH, f"//option[@value='{month}']")))
            month_option.click()
            
            # Select day
            day_select = self.wait.until(EC.presence_of_element_located((By.XPATH, "//select[@title='Gün:']")))
            self.move_mouse_randomly()
            day_select.click()
            self.random_sleep()
            day_option = self.wait.until(EC.presence_of_element_located((By.XPATH, f"//option[@value='{day}']")))
            day_option.click()
            
            # Select year
            year_select = self.wait.until(EC.presence_of_element_located((By.XPATH, "//select[@title='Yıl:']")))
            self.move_mouse_randomly()
            year_select.click()
            self.random_sleep()
            year_option = self.wait.until(EC.presence_of_element_located((By.XPATH, f"//option[@value='{year}']")))
            year_option.click()

                        # Click next button
            next_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='İleri']")))
            self.move_mouse_randomly()
            next_button.click()
            self.random_sleep(3, 5)

            # Wait for verification code page
            code_input = self.wait.until(EC.presence_of_element_located((By.NAME, "email_confirmation_code")))
            logging.info("Waiting for verification code...")

            # Wait for verification code and enter it
            verification_code = self.dropmail.wait_for_verification_code()
            if not verification_code:
                raise Exception("Failed to get verification code")

            self.move_mouse_randomly()
            self.human_type(code_input, verification_code)
            self.random_sleep(1, 2)
            code_input.send_keys(Keys.RETURN)
            self.random_sleep(4, 6)

            # Save account details
            self.save_account(email, username, password, full_name)
            logging.info("Account created successfully!")
            return True

        except Exception as e:
            logging.error(f"Error during account creation: {str(e)}")
            screenshot_path = f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.driver.save_screenshot(screenshot_path)
            logging.error(f"Error screenshot saved to: {screenshot_path}")
            return False

    def save_account(self, email, username, password, full_name):
        """Save account details"""
        try:
            with open('instagram_accounts.txt', 'a', encoding='utf-8') as f:
                f.write(f"\nRegistration Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Email: {email}\n")
                f.write(f"Username: {username}\n")
                f.write(f"Password: {password}\n")
                f.write(f"Full Name: {full_name}\n")
                f.write("-" * 50 + "\n")
            logging.info("Account details saved successfully")
        except Exception as e:
            logging.error(f"Error saving account details: {str(e)}")

    def close(self):
        """Close browser"""
        try:
            if self.driver:
                self.driver.quit()
        except Exception as e:
            logging.error(f"Error closing driver: {str(e)}")

def main():
    """Main program loop"""
    logging.info("Starting Instagram Account Creator with Anti-Detection...")
    
    bot = None
    try:
        bot = InstagramBot()
        max_attempts = 3
        current_attempt = 0
        
        while current_attempt < max_attempts:
            logging.info(f"Attempt {current_attempt + 1} of {max_attempts}")
            
            try:
                if bot.create_account():
                    logging.info("Account creation successful!")
                    break
                else:
                    current_attempt += 1
                    if current_attempt < max_attempts:
                        wait_time = random.randint(30, 60)  # 5-10 minutes
                        logging.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
            except Exception as e:
                logging.error(f"Error during attempt {current_attempt + 1}: {str(e)}")
                current_attempt += 1
                if current_attempt < max_attempts:
                    wait_time = random.randint(60, 120)  # 10-15 minutes
                    logging.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
        
    except KeyboardInterrupt:
        logging.info("Program terminated by user")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
    finally:
        if bot:
            bot.close()
        logging.info("Program terminated")

if __name__ == "__main__":
    main()