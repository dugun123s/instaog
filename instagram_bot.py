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
from faker import Faker
import logging
import time
import random
import requests
import json
import re
from datetime import datetime

# Logging ayarları
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
            
            response = self.session.post(
                self.api_url,
                headers=self.headers,
                json={'query': query}
            )
            
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
                
                variables = {
                    'sessionId': self.session_id
                }

                response = self.session.post(
                    self.api_url,
                    headers=self.headers,
                    json={
                        'query': query,
                        'variables': variables
                    }
                )

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

class InstagramBot:
    def __init__(self):
        self.fake = Faker('tr_TR')
        self.dropmail = DropMailClient()
        
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-notifications')
        
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        chrome_options.add_argument(f'user-agent={user_agent}')
        chrome_options.add_argument('--lang=tr-TR')
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), 
                                     options=chrome_options)
        
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": user_agent
        })
        
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.wait = WebDriverWait(self.driver, 20)
        self.actions = ActionChains(self.driver)
        self.driver.maximize_window()

    def generate_user_data(self):
        """Rastgele kullanıcı bilgileri oluştur"""
        username = f"{self.fake.user_name()}_{random.randint(100,999)}".lower()
        password = f"Pass_{self.fake.password(length=10)}#1"
        full_name = self.fake.name()
        
        username = username.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
        full_name = full_name.replace('İ', 'I').replace('Ğ', 'G').replace('Ü', 'U').replace('Ş', 'S').replace('Ö', 'O').replace('Ç', 'C')
        
        return username, password, full_name

    def generate_birth_date(self):
        """18-50 yaş arası rastgele doğum tarihi oluştur"""
        year = random.randint(1973, 2005)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        return year, month, day

    def random_sleep(self, min_time=1, max_time=3):
        """Random süre bekle"""
        time.sleep(random.uniform(min_time, max_time))

    def human_type(self, element, text):
        """İnsansı yazma davranışı"""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))
        self.random_sleep()

    def move_mouse_randomly(self):
        """Fareyi rastgele hareket ettir"""
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
        """Çerez popup'ını kabul et"""
        try:
            cookie_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Tümünü Kabul Et')]")
            self.move_mouse_randomly()
            cookie_button.click()
            self.random_sleep()
        except:
            pass

    def create_account(self):
        try:
            # Email oluştur
            email = self.dropmail.create_inbox()
            if not email:
                raise Exception("Failed to create email inbox")

            # Kullanıcı bilgilerini oluştur
            username, password, full_name = self.generate_user_data()
            
            # Instagram'ı aç
            self.driver.get("https://www.instagram.com")
            self.random_sleep(3, 5)
            
            # Çerez popup'ını kontrol et
            self.handle_cookie_popup()

            # Kaydol butonuna tıkla
            signup_link = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Kaydol']")))
            self.move_mouse_randomly()
            signup_link.click()
            self.random_sleep(2, 4)

            # Form alanlarını doldur
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

            # Kaydol butonuna tıkla
            submit_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
            self.move_mouse_randomly()
            submit_button.click()
            self.random_sleep(3, 5)

            # Doğum tarihi ekranı
            year, month, day = self.generate_birth_date()
            
            # Ay seçimi
            month_select = self.wait.until(EC.presence_of_element_located((By.XPATH, "//select[@title='Ay:']")))
            self.move_mouse_randomly()
            month_select.click()
            self.random_sleep()
            month_option = self.wait.until(EC.presence_of_element_located((By.XPATH, f"//option[@value='{month}']")))
            month_option.click()
            
            # Gün seçimi
            day_select = self.wait.until(EC.presence_of_element_located((By.XPATH, "//select[@title='Gün:']")))
            self.move_mouse_randomly()
            day_select.click()
            self.random_sleep()
            day_option = self.wait.until(EC.presence_of_element_located((By.XPATH, f"//option[@value='{day}']")))
            day_option.click()
            
            # Yıl seçimi
            year_select = self.wait.until(EC.presence_of_element_located((By.XPATH, "//select[@title='Yıl:']")))
            self.move_mouse_randomly()
            year_select.click()
            self.random_sleep()
            year_option = self.wait.until(EC.presence_of_element_located((By.XPATH, f"//option[@value='{year}']")))
            year_option.click()

            self.random_sleep(1, 2)

            # İleri butonuna tıkla
            next_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='İleri']")))
            self.move_mouse_randomly()
            next_button.click()
            self.random_sleep(3, 5)

            # Doğrulama kodu sayfasını bekle
            code_input = self.wait.until(EC.presence_of_element_located((By.NAME, "email_confirmation_code")))
            logging.info("Waiting for verification code...")

            # Doğrulama kodunu bekle ve gir
            verification_code = self.dropmail.wait_for_verification_code()
            if not verification_code:
                raise Exception("Failed to get verification code")

            self.move_mouse_randomly()
            self.human_type(code_input, verification_code)
            self.random_sleep(1, 2)
            code_input.send_keys(Keys.RETURN)
            self.random_sleep(4, 6)

            # Hesap bilgilerini kaydet
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
        """Hesap bilgilerini kaydet"""
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
        """Tarayıcıyı kapat"""
        try:
            if self.driver:
                self.driver.quit()
        except Exception as e:
            logging.error(f"Error closing driver: {str(e)}")

def main():
    """Ana program döngüsü"""
    logging.info("Starting Instagram Account Creator with Selenium...")
    
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
                        wait_time = random.randint(30, 60)
                        logging.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
            except Exception as e:
                logging.error(f"Error during attempt {current_attempt + 1}: {str(e)}")
                current_attempt += 1
                if current_attempt < max_attempts:
                    wait_time = random.randint(60, 120)
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