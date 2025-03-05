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
        
        # Temel güvenlik ayarları
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # SSL hatalarını önlemek için
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        
        # Web sayfası yükleme stratejisi
        chrome_options.page_load_strategy = 'eager'
        
        # Ek performans ayarları
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        
        # Bellek yönetimi
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        
        # Pencere boyutu ve görünüm
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--start-maximized')
        
        # Bot tespitini önleme
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Bildirimler ve pop-up'ları devre dışı bırak
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--disable-popup-blocking')
        
        # Dil ayarı
        chrome_options.add_argument('--lang=tr-TR')
        
        # User-Agent ayarı
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        chrome_options.add_argument(f'user-agent={user_agent}')

        # Proxy ayarları (isteğe bağlı - kullanmak için yorumu kaldırın)
        # PROXY = "http://kullanici:sifre@ip:port"
        # chrome_options.add_argument(f'--proxy-server={PROXY}')
        
        try:
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), 
                                       options=chrome_options)
            
            # WebDriver gizleme
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['tr-TR', 'tr', 'en-US', 'en']});
                    window.chrome = { runtime: {} };
                '''
            })
            
            # Network ayarları
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": user_agent,
                "platform": "Windows",
                "acceptLanguage": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
            })
            
            # Timeout ve bekleme ayarları
            self.wait = WebDriverWait(self.driver, 20)
            self.driver.set_page_load_timeout(30)
            self.driver.set_script_timeout(30)
            
            self.actions = ActionChains(self.driver)
            self.driver.set_window_size(1920, 1080)
            
        except Exception as e:
            logging.error(f"Chrome başlatma hatası: {str(e)}")
            raise

    def test_connection(self):
        """Instagram bağlantısını test et"""
        try:
            logging.info("Instagram bağlantısı test ediliyor...")
            self.driver.get("https://www.instagram.com")
            time.sleep(5)
            
            # Sayfa yüklenme durumunu kontrol et
            page_state = self.driver.execute_script('return document.readyState;')
            logging.info(f"Sayfa durumu: {page_state}")
            
            # Mevcut URL'i kontrol et
            current_url = self.driver.current_url
            logging.info(f"Mevcut URL: {current_url}")
            
            if "instagram.com" in current_url:
                logging.info("Instagram başarıyla açıldı!")
                return True
            else:
                logging.error("Instagram açılamadı!")
                return False
                
        except Exception as e:
            logging.error(f"Bağlantı testi hatası: {str(e)}")
            return False

    def clear_cookies(self):
        """Cookieleri temizle"""
        try:
            self.driver.delete_all_cookies()
            time.sleep(random.uniform(1, 2))
            logging.info("Cookies temizlendi")
        except Exception as e:
            logging.error(f"Cookie temizleme hatası: {str(e)}")

    def add_random_mouse_movements(self):
        """Sayfa üzerinde rastgele fare hareketleri"""
        try:
            elements = self.driver.find_elements(By.TAG_NAME, "input")
            for _ in range(random.randint(3, 7)):
                if elements:
                    element = random.choice(elements)
                    self.actions.move_to_element_with_offset(
                        element,
                        random.randint(-100, 100),
                        random.randint(-100, 100)
                    ).perform()
                time.sleep(random.uniform(0.1, 0.3))
        except Exception as e:
            logging.error(f"Mouse hareketi hatası: {str(e)}")

    def human_type(self, element, text):
        """Daha gerçekçi insan yazma davranışı"""
        try:
            for char in text:
                time.sleep(random.uniform(0.1, 0.4))
                element.send_keys(char)
                
                if random.random() < 0.05:
                    time.sleep(random.uniform(0.5, 1.5))
            
            time.sleep(random.uniform(0.3, 0.7))
        except Exception as e:
            logging.error(f"Yazma hatası: {str(e)}")

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

    def handle_cookie_popup(self):
        """Çerez popup'ını kabul et"""
        try:
            cookie_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Tümünü Kabul Et')]")
            self.add_random_mouse_movements()
            cookie_button.click()
            self.random_sleep()
        except Exception as e:
            logging.info("Çerez popup'ı bulunamadı veya zaten kabul edildi")

    def create_account(self):
        try:
            if not self.test_connection():
                raise Exception("Instagram'a bağlanılamadı!")
    
            logging.info("Instagram bağlantısı başarılı, işlemlere başlanıyor...")
            
            # Email oluştur
            email = self.dropmail.create_inbox()
            if not email:
                raise Exception("Failed to create email inbox")
            
            # Kullanıcı bilgilerini oluştur
            username, password, full_name = self.generate_user_data()
            
            # Instagram'ı aç
            self.driver.get("https://www.instagram.com")
            self.random_sleep(5, 8)
            
            # Kaydol butonunu bul ve tıkla (güncellendi)
            try:
                signup_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "span._aacl._aaco._aacw._aad0._aad7"))
                )
                signup_button.click()
                self.random_sleep(3, 5)
            except:
                # Alternatif kaydol butonu arama
                try:
                    signup_button = self.driver.find_element(By.XPATH, "//a[contains(@href, '/accounts/emailsignup/')]")
                    signup_button.click()
                    self.random_sleep(3, 5)
                except:
                    logging.error("Kaydol butonu bulunamadı")
                    raise
    
            # Form alanlarını doldur (güncellendi)
            try:
                # Email/Telefon alanı
                email_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[aria-label*='Phone number or email']"))
                )
                self.human_type(email_input, email)
                self.random_sleep(2, 3)
    
                # Ad Soyad alanı
                fullname_input = self.driver.find_element(By.CSS_SELECTOR, "input[aria-label*='Full Name']")
                self.human_type(fullname_input, full_name)
                self.random_sleep(2, 3)
    
                # Kullanıcı adı alanı
                username_input = self.driver.find_element(By.CSS_SELECTOR, "input[aria-label*='Username']")
                self.human_type(username_input, username)
                self.random_sleep(2, 3)
    
                # Şifre alanı
                password_input = self.driver.find_element(By.CSS_SELECTOR, "input[aria-label*='Password']")
                self.human_type(password_input, password)
                self.random_sleep(2, 3)
    
                # Kaydol butonuna tıkla
                submit_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
                )
                submit_button.click()
                self.random_sleep(4, 6)
    
                # Doğum tarihi formu
                try:
                    year, month, day = self.generate_birth_date()
                    
                    # Ay seçimi
                    month_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "select[title*='Month']"))
                    )
                    Select(month_input).select_by_value(str(month))
                    self.random_sleep(1, 2)
    
                    # Gün seçimi
                    day_input = self.driver.find_element(By.CSS_SELECTOR, "select[title*='Day']")
                    Select(day_input).select_by_value(str(day))
                    self.random_sleep(1, 2)
    
                    # Yıl seçimi
                    year_input = self.driver.find_element(By.CSS_SELECTOR, "select[title*='Year']")
                    Select(year_input).select_by_value(str(year))
                    self.random_sleep(1, 2)
    
                    # İleri butonuna tıkla
                    next_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='button']._acan._acap._acas._aj1-"))
                    )
                    next_button.click()
                    self.random_sleep(4, 6)
    
                except Exception as e:
                    logging.error(f"Doğum tarihi form hatası: {str(e)}")
                    # Screenshot al
                    self.driver.save_screenshot(f"birthday_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                    # Hatayı göster ama devam et
                    pass
    
                # Doğrulama kodu girişi
                try:
                    code_input = WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "input[aria-label*='Confirmation']"))
                    )
                    logging.info("Doğrulama kodu bekleniyor...")
                    
                    verification_code = self.dropmail.wait_for_verification_code()
                    if not verification_code:
                        raise Exception("Doğrulama kodu alınamadı")
    
                    self.human_type(code_input, verification_code)
                    self.random_sleep(1, 2)
                    
                    # Doğrulama butonuna tıkla
                    confirm_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
                    )
                    confirm_button.click()
                    self.random_sleep(4, 6)
    
                except Exception as e:
                    logging.error(f"Doğrulama kodu hatası: {str(e)}")
                    self.driver.save_screenshot(f"verification_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                    raise
    
                # Hesap bilgilerini kaydet
                self.save_account(email, username, password, full_name)
                logging.info("Hesap başarıyla oluşturuldu!")
                return True
    
            except Exception as e:
                logging.error(f"Form doldurma hatası: {str(e)}")
                self.driver.save_screenshot(f"form_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                raise
    
        except Exception as e:
            logging.error(f"Hesap oluşturma hatası: {str(e)}")
            screenshot_path = f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.driver.save_screenshot(screenshot_path)
            logging.error(f"Hata ekran görüntüsü kaydedildi: {screenshot_path}")
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
    
    while True:
        try:
            bot = InstagramBot()
            
            # Her yeni oturum için cookie ve önbellek temizliği
            bot.clear_cookies()
            
            # Hesap oluştur
            if bot.create_account():
                logging.info("Account created successfully!")
                
                # Tarayıcıyı kapat
                bot.close()
                
                # Sonraki hesap oluşturma işlemi öncesi uzun bekleme
                wait_time = random.randint(300, 900)  # 5-15 dakika arası
                logging.info(f"Waiting {wait_time} seconds before next account creation...")
                time.sleep(wait_time)
            else:
                # Hata durumunda daha uzun bekle
                wait_time = random.randint(900, 1800)  # 15-30 dakika arası
                logging.warning(f"Failed to create account. Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            
        except KeyboardInterrupt:
            logging.info("Program terminated by user")
            break
        except Exception as e:
            logging.error(f"Error in main loop: {str(e)}")
            time.sleep(120)
        finally:
            if 'bot' in locals():
                bot.close()

    logging.info("Program terminated")

if __name__ == "__main__":
    main()