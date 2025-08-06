import argparse
import time
from typing import Optional, List
from dataclasses import dataclass, field

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup

# --- 1. Структура для хранения данных ---
@dataclass
class Post:
    """Удобная структура для хранения данных о посте."""
    # --- Сначала все обязательные поля ---
    author: str
    text: str = field(repr=False) # repr=False по-прежнему здесь, чтобы не выводить текст

    # --- Затем все необязательные поля ---
    post_id: Optional[str] = None

# --- 2. Функция для получения HTML (Ваш код, немного доработанный) ---
def get_page_html(url: str, driver: webdriver.Chrome) -> Optional[str]:
    """
    Загружает одну страницу по URL и возвращает ее HTML.
    Использует уже существующий экземпляр драйвера.
    """
    try:
        print(f"Открываю страницу: {url}")
        driver.get(url)

        # Ваше работающее условие ожидания - это отлично!
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "block-title")))

        print("Контент загружен.")
        return driver.page_source
    except TimeoutException:
        print(f"Не дождался загрузки контента на странице: {url}")
        return None
    except Exception as e:
        print(f"Произошла ошибка при загрузке страницы {url}: {e}")
        return None

# --- 3. Функция для парсинга данных из HTML ---
def parse_posts_from_html(html: str) -> List[Post]:
    """
    Извлекает все посты (автор, текст) из предоставленного HTML.
    """
    soup = BeautifulSoup(html, 'lxml')
    parsed_posts: List[Post] = []

    # Ищем все контейнеры постов по уникальному атрибуту `data-post`
    post_containers = soup.find_all('table', attrs={'data-post': True})

    for container in post_containers:
        author_tag = container.find('span', class_='normalname')
        post_body_tag = container.find('div', class_='postcolor')

        if author_tag and post_body_tag:
            author = author_tag.text.strip()
            # get_text() с параметрами - лучший способ извлечь чистый текст
            text = post_body_tag.get_text(strip=True, separator='\n')
            post_id = container.get('data-post')
            parsed_posts.append(Post(author=author, text=text, post_id=post_id))

    return parsed_posts

# --- 4. Основной блок выполнения ---
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Scraper and Importer Pipeline for scraping and importing.")
    parser.add_argument("--url", required=True, help="URL of the topic to scrape.")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages to scrape.")
    # Добавляем новый флаг
    parser.add_argument(
        "--non-interactive",
        action="store_true", # Этот флаг не требует значения, его наличие означает True
        help="Run in non-interactive mode for CI/CD environments."
    )
    args = parser.parse_args()
    # Устанавливаем базовый URL и количество страниц для парсинга
    base_url = "https://example.com"
    pages_to_parse = 2 # Для примера возьмем первые 2 страницы

    # Настройка Selenium
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36')

    driver: Optional[webdriver.Chrome] = None
    all_posts: List[Post] = []

    try:
        service = ChromeService()
        driver = webdriver.Chrome(service=service, options=options)

        # Цикл для прохода по страницам
        for page_num in range(pages_to_parse):
            # Вычисляем смещение для URL (st=0, st=20, st=40, ...)
            start_offset = page_num * 20
            page_url = f"{base_url}&st={start_offset}"

            html_content = get_page_html(page_url, driver)

            if html_content:
                posts_on_page = parse_posts_from_html(html_content)
                if posts_on_page:
                    print(f"На странице {page_num + 1} найдено {len(posts_on_page)} постов.")
                    all_posts.extend(posts_on_page)
                else:
                    print(f"На странице {page_num + 1} посты не найдены.")

            # Небольшая пауза между запросами, чтобы не нагружать сайт
            time.sleep(2)

    finally:
        if driver:
            print("Закрываю браузер.")
            driver.quit()

    # Выводим итоговый результат
    print(f"\n\n--- ВСЕГО СОБРАНО {len(all_posts)} ПОСТОВ ---\n")
    for i, post in enumerate(all_posts, 1):
        print(f"--- Пост #{i} (Автор: {post.author}) ---")
        print(f"{post.text[:200].strip()}...")
        print("-" * 20)

