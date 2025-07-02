import json
import random
import time
import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager

# --- НАСТРОЙКИ ---
TARGET_URL = 'https://msk.kassir.ru/category?sort=0'
CLICK_COUNT = 5
RUCAPTCHA_API_KEY = '863b567c1d376398b65ad121498f89a1'  # 🔴 ЗАМЕНИ НА СВОЙ КЛЮЧ


class KassirScraper:
    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        self.wait = WebDriverWait(self.driver, 15)

    def handle_popups(self):
        try:
            confirm_btn = WebDriverWait(self.driver, 7).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Всё верно')]"))
            )
            confirm_btn.click()
            time.sleep(1)
        except TimeoutException:
            pass

    def solve_captcha_with_rucaptcha(self):
        try:
            print("🛑 Обнаружена капча. Решаю через RuCaptcha...")
            captcha_div = self.driver.find_element(By.ID, "captcha-container")
            sitekey = captcha_div.get_attribute("data-sitekey")
            page_url = self.driver.current_url

            payload = {
                'method': 'yandex',
                'key': RUCAPTCHA_API_KEY,
                'sitekey': sitekey,
                'pageurl': page_url,
                'json': 1
            }

            response = requests.post("http://rucaptcha.com/in.php", data=payload).json()
            if response.get("status") != 1:
                print("❌ Ошибка отправки:", response)
                return False

            captcha_id = response["request"]

            for _ in range(24):
                time.sleep(5)
                result = requests.get("http://rucaptcha.com/res.php", params={
                    'key': RUCAPTCHA_API_KEY,
                    'action': 'get',
                    'id': captcha_id,
                    'json': 1
                }).json()

                if result.get("status") == 1:
                    smart_token = result["request"]
                    break
            else:
                print("❌ Время ожидания капчи истекло.")
                return False

            token_input = self.driver.find_element(By.CSS_SELECTOR, 'input[name="smart-token"]')
            self.driver.execute_script("arguments[0].setAttribute('value', arguments[1])", token_input, smart_token)
            form = self.driver.find_element(By.ID, "j-captcha-form")
            form.submit()

            time.sleep(3)
            return True

        except Exception as e:
            print(f"❌ Ошибка при решении капчи: {e}")
            return False

    def run(self):
        all_events_data = []

        try:
            print(f"🌐 Открываю сайт: {TARGET_URL}")
            self.driver.get(TARGET_URL)

            if "smartcaptcha.yandexcloud.net" in self.driver.page_source:
                if not self.solve_captcha_with_rucaptcha():
                    print("❌ Капчу не удалось пройти.")
                    return []

            self.handle_popups()

            show_more_selector = (By.CSS_SELECTOR, 'button[data-selenide="getNextExtraCompilationButton"]')

            for i in range(CLICK_COUNT):
                try:
                    print(f"🔘 Клик по 'Показать ещё' ({i + 1}/{CLICK_COUNT})")
                    show_more_button = self.wait.until(EC.element_to_be_clickable(show_more_selector))
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", show_more_button)
                    time.sleep(random.uniform(1.5, 3.5))
                    show_more_button.click()
                    time.sleep(random.uniform(2.5, 4.5))
                except (TimeoutException, ElementClickInterceptedException):
                    print("⚠️ Больше кнопка недоступна.")
                    break

            card_selector = (By.CSS_SELECTOR, 'li[data-index]')
            self.wait.until(EC.presence_of_element_located(card_selector))
            cards = self.driver.find_elements(*card_selector)

            for i, card in enumerate(cards):
                data = {}

                try:
                    title = card.find_element(By.CSS_SELECTOR, 'h2[class*="recommendation-item_title"]')
                    data['title'] = title.text
                    link = card.find_element(By.CSS_SELECTOR, 'a[href]')
                    data['link'] = link.get_attribute("href")
                except:
                    data['title'] = None
                    data['link'] = None

                try:
                    price = card.find_element(By.CSS_SELECTOR, 'li[class*="recommendation-item_price-block"]').text
                    data['price_text'] = price.replace('\n', ' ').strip()
                except:
                    data['price_text'] = 'Цена не указана'

                try:
                    date = card.find_element(By.CSS_SELECTOR, 'time[class*="recommendation-item_date"]').text
                    data['date_text'] = date.replace('\n', ' ').strip()
                except:
                    data['date_text'] = 'Дата не указана'

                if data['title']:
                    all_events_data.append(data)
                    print(f"\n🔹 {data['title']}")
                    print(f"   📅 {data['date_text']}")
                    print(f"   💸 {data['price_text']}")
                    print(f"   🔗 {data['link']}")
                else:
                    print(f"❌ Пропущена карточка #{i + 1}")

            print(f"\n✅ Всего собрано событий: {len(all_events_data)}")
            return all_events_data

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return []
        finally:
            self.driver.quit()
            print("🛑 Браузер закрыт.")


if __name__ == '__main__':
    scraper = KassirScraper()
    events = scraper.run()
    # Здесь переменная `events` содержит весь список собранных ивентов