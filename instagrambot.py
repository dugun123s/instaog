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
import os
from datetime import datetime
from pathlib import Path
import pyautogui
import sys
import warnings
warnings.filterwarnings("ignore")

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
        """Yeni bir geçici e-posta oluştur"""
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
        """E-posta doğrulama kodunu bekle"""
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

class ProxyManager:
    def __init__(self):
        self.proxies = self.load_proxies()
        
    def load_proxies(self):
        """Proxy listesini dosyadan yükle"""
        try:
            with open('proxies.txt', 'r') as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            logging.warning("proxies.txt file not found. Running without proxies.")
            return []
            
    def get_random_proxy(self):
        """Rastgele bir proxy seç"""
        if self.proxies:
            return random.choice(self.proxies)
        return None

class Browser:
    """Tarayıcı parmak izi yönetimi"""
    @staticmethod
    def modify_navigator(driver):
        """Navigator özelliklerini modifiye et"""
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
            driver.execute_script(f"Object.defineProperty(navigator, '{key}', "
                                f"{{get: () => {str(value).lower()}}});")

    @staticmethod
    def modify_window_properties(driver):
        """Window özelliklerini modifiye et"""
        window_modifications = {
            'callPhantom': False,
            '_phantom': False,
            'phantom': False,
            'webdriver': False,
            '__nightmare': False
        }
        
        for key, value in window_modifications.items():
            driver.execute_script(f"Object.defineProperty(window, '{key}', "
                                f"{{get: () => {str(value).lower()}}});")

    @staticmethod
    def add_mock_scripts(driver):
        """Sahte script elemanları ekle"""
        mock_scripts = [
            "const newProto = navigator.__proto__;",
            "delete newProto.webdriver;",
            "navigator.__proto__ = newProto;",
            "const originalQuery = window.navigator.permissions.query;",
            "window.navigator.permissions.query = (parameters) => (",
            "    parameters.name === 'notifications' ?",
            "    Promise.resolve({state: Notification.permission}) :",
            "    originalQuery(parameters)",
            ");"
        ]
        for script in mock_scripts:
            driver.execute_script(script)

    @staticmethod
    def add_mock_elements(driver):
        """Sahte DOM elemanları ekle"""
        mock_elements = [
            ("div", {"id": "selenium-ide-indicator", "style": "display:none"}),
            ("div", {"id": "webdriver-indicator", "style": "display:none"}),
            ("div", {"id": "selenium-indicator", "style": "display:none"})
        ]
        for tag, attrs in mock_elements:
            attrs_str = ' '.join([f'{k}="{v}"' for k, v in attrs.items()])
            driver.execute_script(
                f"document.body.insertAdjacentHTML('beforeend', '<{tag} {attrs_str}></{tag}>')"
            )

class InstagramBot:
    def __init__(self, use_proxy=True):
        self.fake = Faker('tr_TR')
        self.dropmail = DropMailClient()
        self.proxy_manager = ProxyManager()
        
        # Undetected Chrome Driver kullanımı
        options = uc.ChromeOptions()
        
        # Gerçek bir kullanıcı aracısı kullan
        ua = UserAgent()
        user_agent = ua.random
        options.add_argument(f'user-agent={user_agent}')
        
        # Dil ayarı
        options.add_argument('--lang=tr-TR')
        
        # Proxy kullanımı
        if use_proxy:
            proxy = self.proxy_manager.get_random_proxy()
            if proxy:
                options.add_argument(f'--proxy-server={proxy}')
        
        # Gerçek profil oluştur
        profile_path = Path.home() / "instagram_bot_profile"
        options.add_argument(f'--user-data-dir={str(profile_path)}')
        
        # WebGL ve Canvas parmak izini rastgele yap
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Diğer gizlilik ayarları
        options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        options.add_argument('--disable-site-isolation-trials')
        
        # Undetected Chrome Driver başlat
        self.driver = uc.Chrome(options=options)
        
        # Pencere boyutu rastgele
        screen_width = 1920
        screen_height = 1080
        window_width = random.randint(1024, screen_width)
        window_height = random.randint(768, screen_height)
        self.driver.set_window_size(window_width, window_height)
        
        self.wait = WebDriverWait(self.driver, 20)
        self.actions = ActionChains(self.driver)
        
        # Browser anti-detection
        Browser.modify_navigator(self.driver)
        Browser.modify_window_properties(self.driver)
        Browser.add_mock_scripts(self.driver)
        Browser.add_mock_elements(self.driver)

    def random_sleep(self, min_time=1, max_time=3):
        """Random süre bekle"""
        time.sleep(random.uniform(min_time, max_time))

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

    def human_type(self, element, text):
        """İnsansı yazma davranışı"""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))
        self.random_sleep()

    def handle_cookie_popup(self):
        """Çerez popup'ını kabul et"""
        try:
            cookie_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Tümünü Kabul Et')]")
            self.move_mouse_randomly()
            cookie_button.click()
            self.random_sleep()
        except:
            pass

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

    def simulate_human_behavior(self):
        """İnsan davranışlarını simüle et"""
        # Sayfayı rastgele scroll
        scroll_amount = random.randint(300, 700)
        self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        self.random_sleep(0.5, 1.5)
        
        # Fareyi rastgele hareket ettir
        self.move_mouse_randomly()
        
        # Sayfayı yukarı kaydır
        self.driver.execute_script("window.scrollTo(0, 0);")
        self.random_sleep(0.5, 1)

    def post_registration_actions(self):
        """Hesap oluşturulduktan sonra gerçek kullanıcı davranışları"""
        try:
            # Profil fotoğrafı yükle
            self.upload_profile_photo()
            
            # Birkaç popüler hesabı takip et
            self.follow_popular_accounts()
            
            # Bio güncelle
            self.update_bio()
            
            # Hikayelere göz at
            self.view_stories()
            
            # Keşfet sayfasında gezin
            self.browse_explore_page()
            
        except Exception as e:
            logging.error(f"Error in post registration actions: {str(e)}")

    def upload_profile_photo(self):
        """Profil fotoğrafı yükle"""
        try:
            # Profil sayfasına git
            self.driver.get(f"https://www.instagram.com/accounts/edit/")
            self.random_sleep(2, 4)
            
            # Profil fotoğrafı değiştir butonu
            change_photo_button = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, "//button[contains(text(), 'Fotoğrafı Değiştir')]")))
            self.move_mouse_randomly()
            change_photo_button.click()
            self.            random_sleep(1, 2)
            
            # Profil fotoğrafını yükle
            photo_path = os.path.join('profile_photos', random.choice(os.listdir('profile_photos')))
            pyautogui.write(str(Path(photo_path).absolute()))
            pyautogui.press('enter')
            self.random_sleep(3, 5)
            
        except Exception as e:
            logging.error(f"Error uploading profile photo: {str(e)}")

    def follow_popular_accounts(self):
        """Popüler hesapları takip et"""
        popular_accounts = ['instagram', 'cristiano', 'leomessi', 'beyonce', 'arianagrande']
        random.shuffle(popular_accounts)
        
        for account in popular_accounts[:3]:  # Rastgele 3 hesap takip et
            try:
                self.driver.get(f"https://www.instagram.com/{account}/")
                self.random_sleep(2, 4)
                
                follow_button = self.wait.until(EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(., 'Takip Et')]")))
                self.move_mouse_randomly()
                follow_button.click()
                self.random_sleep(3, 5)
                
            except Exception as e:
                logging.error(f"Error following {account}: {str(e)}")
                continue

    def update_bio(self):
        """Profil biyografisini güncelle"""
        try:
            self.driver.get("https://www.instagram.com/accounts/edit/")
            self.random_sleep(2, 4)
            
            bio_input = self.wait.until(EC.presence_of_element_located(
                (By.ID, "pepBio")))
            
            bio_text = self.generate_bio()
            self.move_mouse_randomly()
            self.human_type(bio_input, bio_text)
            
            submit_button = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'Gönder')]")))
            self.move_mouse_randomly()
            submit_button.click()
            self.random_sleep(2, 3)
            
        except Exception as e:
            logging.error(f"Error updating bio: {str(e)}")

    def generate_bio(self):
        """Rastgele biyografi oluştur"""
        bios = [
            "🌟 Hayat güzeldir",
            "📸 Fotoğraf tutkunu",
            "🎵 Müzik = Hayat",
            "✨ Pozitif enerji",
            "🌍 Gezgin ruh",
            "💫 Hayal et ve başar",
            "🎨 Sanat aşığı",
            "📚 Kitap kurdu"
        ]
        return random.choice(bios)

    def view_stories(self):
        """Hikayeleri görüntüle"""
        try:
            self.driver.get("https://www.instagram.com")
            self.random_sleep(3, 5)
            
            # İlk hikayeye tıkla
            story = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, "//div[@class='_aac4 _aac5 _aac6']")))
            self.move_mouse_randomly()
            story.click()
            
            # Birkaç hikaye izle
            for _ in range(random.randint(3, 7)):
                self.random_sleep(2, 4)
                # Sonraki hikayeye geç
                self.actions.send_keys(Keys.ARROW_RIGHT).perform()
            
            # Hikayeleri kapat
            self.actions.send_keys(Keys.ESCAPE).perform()
            self.random_sleep(1, 2)
            
        except Exception as e:
            logging.error(f"Error viewing stories: {str(e)}")

    def browse_explore_page(self):
        """Keşfet sayfasında gezin"""
        try:
            self.driver.get("https://www.instagram.com/explore/")
            self.random_sleep(3, 5)
            
            # Sayfayı rastgele scroll
            for _ in range(random.randint(3, 7)):
                scroll_amount = random.randint(300, 700)
                self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                self.random_sleep(1, 3)
            
        except Exception as e:
            logging.error(f"Error browsing explore page: {str(e)}")

    def fill_registration_form(self, email, full_name, username, password):
        """Kayıt formunu doldur"""
        fields = {
            "emailOrPhone": email,
            "fullName": full_name,
            "username": username,
            "password": password
        }
        
        for field_name, value in fields.items():
            field = self.wait.until(EC.presence_of_element_located((By.NAME, field_name)))
            self.move_mouse_randomly()
            self.human_type(field, value)
            self.random_sleep(0.5, 1.5)

    def fill_birth_date(self):
        """Doğum tarihi formunu doldur"""
        try:
            year, month, day = self.generate_birth_date()
            
            # Ay seçimi
            month_select = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, "//select[@title='Ay:']")))
            self.move_mouse_randomly()
            month_select.click()
            self.random_sleep()
            month_option = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, f"//option[@value='{month}']")))
            month_option.click()
            
            # Gün seçimi
            day_select = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, "//select[@title='Gün:']")))
            self.move_mouse_randomly()
            day_select.click()
            self.random_sleep()
            day_option = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, f"//option[@value='{day}']")))
            day_option.click()
            
            # Yıl seçimi
            year_select = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, "//select[@title='Yıl:']")))
            self.move_mouse_randomly()
            year_select.click()
            self.random_sleep()
            year_option = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, f"//option[@value='{year}']")))
            year_option.click()
            
            self.random_sleep(1, 2)
            
            # İleri butonuna tıkla
            next_button = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[text()='İleri']")))
            self.move_mouse_randomly()
            next_button.click()
            self.random_sleep(2, 4)
            
        except Exception as e:
            logging.error(f"Error filling birth date: {str(e)}")
            raise

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
            signup_link = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//span[text()='Kaydol']")))
            self.move_mouse_randomly()
            signup_link.click()
            self.random_sleep(2, 4)

            # Form alanlarını doldur
            self.fill_registration_form(email, full_name, username, password)
            
            # Doğum tarihi ekranı
            self.fill_birth_date()
            
            # Doğrulama kodunu bekle ve gir
            if not self.handle_verification(email):
                raise Exception("Verification failed")
            
            # Hesap oluşturulduktan sonraki işlemler
            self.random_sleep(5, 8)
            self.post_registration_actions()

            # Hesap bilgilerini kaydet
            self.save_account(email, username, password, full_name)
            logging.info("Account created successfully!")
            return True

        except Exception as e:
            logging.error(f"Error during account creation: {str(e)}")
            self.take_error_screenshot()
            return False

    def handle_verification(self, email):
        """Doğrulama kodunu işle"""
        try:
            code_input = self.wait.until(EC.presence_of_element_located(
                (By.NAME, "email_confirmation_code")))
            verification_code = self.dropmail.wait_for_verification_code()
            
            if not verification_code:
                return False
                
            self.move_mouse_randomly()
            self.human_type(code_input, verification_code)
            self.random_sleep(1, 2)
            code_input.send_keys(Keys.RETURN)
            self.random_sleep(4, 6)
            return True
            
        except Exception as e:
            logging.error(f"Error during verification: {str(e)}")
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

    def take_error_screenshot(self):
        """Hata durumunda ekran görüntüsü al"""
        try:
            screenshot_dir = Path("error_screenshots")
            screenshot_dir.mkdir(exist_ok=True)
            
            screenshot_path = screenshot_dir / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.driver.save_screenshot(str(screenshot_path))
            logging.error(f"Error screenshot saved to: {screenshot_path}")
            
        except Exception as e:
            logging.error(f"Error taking screenshot: {str(e)}")

    def close(self):
        """Tarayıcıyı kapat"""
        try:
            if self.driver:
                self.driver.quit()
        except Exception as e:
            logging.error(f"Error closing driver: {str(e)}")

def main():
    """Ana program döngüsü"""
    logging.info("Starting Instagram Account Creator with Anti-Detection...")
    
    bot = None
    try:
        bot = InstagramBot(use_proxy=True)
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
                        wait_time = random.randint(300, 600)  # 5-10 dakika bekle
                        logging.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
            except Exception as e:
                logging.error(f"Error during attempt {current_attempt + 1}: {str(e)}")
                current_attempt += 1
                if current_attempt < max_attempts:
                    wait_time = random.randint(600, 900)  # 10-15 dakika bekle
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