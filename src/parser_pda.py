# parser_pda.py — Парсер для 4pda.to.
"""
Финальная, наиболее надежная версия парсера для 4pda.to.

Ключевые особенности:
1.  **Усиленная маскировка под браузер:** Использует профиль Chrome и специальные
    наборы шифров (Cipher Suites) для обхода защиты TLS.
2.  **Автоматические повторные попытки (Retries):** При возникновении сетевых ошибок
    (ConnectionResetError, SSLError) скрипт не падает, а делает несколько
    повторных попыток с возрастающей задержкой.
3.  **Точный анализ контента:** Использует надежный метод для поиска спойлера
    "ПРОМПТЫ" и извлечения из него ссылок с описаниями.
4.  **Полная структура и логирование:** Код полностью структурирован с использованием
    датаклассов и выводит подробную информацию о ходе своей работы.
"""

import configparser
import logging
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin, urlparse, parse_qs

import cloudscraper
from bs4 import BeautifulSoup, Tag
# Импортируем исключения для точной обработки ошибок
from requests.exceptions import RequestException
from ssl import SSLError

# --- 1. НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


# --- 2. СТРУКТУРЫ ДАННЫХ ---
@dataclass(frozen=True)
class PostData:
    author: str
    content: str
    published_at: datetime
    page: int
    post_id: int
    content_html: Optional[Tag]

@dataclass(frozen=True)
class PromptLink:
    url: str
    description: str

@dataclass(frozen=True)
class IndexAnalysisResult:
    last_modified_date: Optional[datetime]
    prompt_links: List[PromptLink]


# --- 3. ФУНКЦИИ-ПОМОЩНИКИ ---

def parse_datetime(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, '%d.%m.%y, %H:%M')
    except (ValueError, TypeError):
        return datetime.min

# --- НОВАЯ ФУНКЦИЯ: НАДЕЖНЫЙ ЗАПРОС С ПОВТОРАМИ ---
def make_request_with_retries(
        scraper: cloudscraper.CloudScraper,
        url: str,
        retries: int = 3,
        backoff_factor: float = 1.5
) -> Optional[cloudscraper.requests.Response]:
    """
    Выполняет HTTP-запрос, автоматически повторяя его при сетевых ошибках.

    Args:
        scraper: Экземпляр cloudscraper.
        url: URL для запроса.
        retries: Количество повторных попыток.
        backoff_factor: Множитель для увеличения задержки между попытками.

    Returns:
        Объект Response в случае успеха, иначе None.
    """
    for i in range(retries):
        try:
            response = scraper.get(url, timeout=30)
            response.raise_for_status()  # Проверить на HTTP ошибки 4xx/5xx
            return response
        except (RequestException, SSLError) as e:
            logging.warning(f"Попытка [{i+1}/{retries}] не удалась для {url}. Ошибка: {e}")
            if i < retries - 1:
                delay = backoff_factor * (2 ** i)  # Экспоненциальная задержка
                logging.info(f"Ждем {delay:.2f} секунд перед следующей попыткой...")
                time.sleep(delay)
    logging.error(f"Все {retries} попыток для {url} провалились.")
    return None

def _extract_post_data_from_table(post_table: Tag, page_num: int) -> Optional[PostData]:
    # ... (эта функция без изменений)
    if not post_table.has_attr('data-post'): return None
    try: post_id = int(post_table['data-post'])
    except (ValueError, KeyError): return None
    author_element = post_table.find('span', class_='normalname')
    author = author_element.text.strip() if author_element else "N/A"
    content_element = post_table.find('div', class_='postcolor')
    if not content_element: return None
    content_text = content_element.get_text(separator='\n', strip=True)
    date_str = ""
    date_cells = post_table.find_all('td', class_='row2')
    if len(date_cells) > 1:
        match = re.search(r'(\d{2}\.\d{2}\.\d{2}, \d{2}:\d{2})', date_cells[1].get_text())
        if match: date_str = match.group(1)
    return PostData(author=author, content=content_text, published_at=parse_datetime(date_str), page=page_num, post_id=post_id, content_html=content_element)


# --- 4. ОСНОВНЫЕ ФУНКЦИИ ПАРСИНГА ---

def parse_topic_page(scraper: cloudscraper.CloudScraper, url: str) -> Optional[List[PostData]]:
    logging.info(f"Парсим страницу: {url}")
    response = make_request_with_retries(scraper, url)
    if not response:
        return None

    try:
        soup = BeautifulSoup(response.text, 'lxml')
        page_num_element = soup.find('span', class_='pagecurrent-wa')
        current_page = int(page_num_element.text.strip()) if page_num_element else 1
        post_elements = soup.find_all('table', attrs={'data-post': True})
        return [post for post_table in post_elements if (post := _extract_post_data_from_table(post_table, current_page))]
    except Exception as e:
        logging.error(f"Ошибка при обработке HTML страницы {url}: {e}", exc_info=True)
        return None

def analyze_index_post(post: PostData, base_url: str) -> IndexAnalysisResult:
    # ... (эта функция без изменений, она работала правильно)
    if not post.content_html:
        logging.warning("HTML-содержимое поста отсутствует.")
        return IndexAnalysisResult(None, [])

    last_modified_date = None
    edit_match = re.search(r"Сообщение отредактировал.*? - (\d{2}\.\d{2}\.\d{2}, \d{2}:\d{2})", post.content, re.DOTALL)
    if edit_match:
        last_modified_date = parse_datetime(edit_match.group(1))
        logging.info(f"Найдена дата редактирования: {last_modified_date.strftime('%Y-%m-%d %H:%M')}")

    prompt_links: List[PromptLink] = []
    spoiler_title_tag = post.content_html.find('div', class_='block-title', string=re.compile(r'^\s*ПРОМПТЫ\s*$', re.IGNORECASE))

    if not spoiler_title_tag:
        logging.warning("Спойлер 'ПРОМПТЫ' не найден.")
        return IndexAnalysisResult(last_modified_date, [])

    spoiler_container = spoiler_title_tag.find_parent('div', class_='post-block')

    if not spoiler_container:
        logging.warning("Не найден родительский контейнер '.post-block' для спойлера.")
        return IndexAnalysisResult(last_modified_date, [])

    logging.info("Найден контейнер спойлера. Ищем все ссылки внутри него...")
    all_links_in_container = spoiler_container.find_all('a', href=True)

    processed_urls = set()
    for link_tag in all_links_in_container:
        href = link_tag.get('href', '')
        if 'showpost=' in href or 'p=' in href:
            full_url = urljoin(base_url, href)
            if full_url not in processed_urls:
                description = link_tag.get_text(strip=True)
                prompt_links.append(PromptLink(url=full_url, description=description))
                processed_urls.add(full_url)

    logging.info(f"Итог: Найдено {len(prompt_links)} уникальных ссылок на промпты.")
    return IndexAnalysisResult(last_modified_date=last_modified_date, prompt_links=prompt_links)


def parse_single_post_by_url(scraper: cloudscraper.CloudScraper, url: str) -> Optional[PostData]:
    # ... (эта функция тоже использует новый надежный запрос)
    response = make_request_with_retries(scraper, url)
    if not response:
        return None

    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        post_id_list = query_params.get('p') or query_params.get('showpost')

        if not post_id_list:
            logging.warning(f"Не удалось извлечь ID поста из URL: {url}")
            return None

        target_post_id = post_id_list[0]
        logging.info(f"Целевой парсинг поста ID {target_post_id}")
        soup = BeautifulSoup(response.text, 'lxml')
        post_table = soup.find('table', attrs={'data-post': target_post_id})

        if not post_table:
            logging.error(f"Не удалось найти пост с ID {target_post_id} на странице {url}")
            return None

        page_num_element = soup.find('span', class_='pagecurrent-wa')
        page_num = int(page_num_element.text.strip()) if page_num_element else 0
        return _extract_post_data_from_table(post_table, page_num)
    except Exception as e:
        logging.error(f"Ошибка при обработке HTML одиночного поста {url}: {e}", exc_info=True)
        return None


# --- 5. ГЛАВНАЯ ФУНКЦИЯ ---
def main():
    try:
        config_path = Path(__file__).parent / 'config.ini'
        logging.info(f"Ищем файл конфигурации: {config_path}")
        config = configparser.ConfigParser()
        if not config.read(config_path, encoding='utf-8-sig'):
            raise FileNotFoundError(f"Файл конфигурации не найден: {config_path}")
        # ... (чтение конфига)
        domain = config.get('Target', 'domain')
        topic_path = config.get('Target', 'topic_path')
        min_delay = config.getfloat('ParserSettings', 'min_delay_seconds')
        max_delay = config.getfloat('ParserSettings', 'max_delay_seconds')
        cookies_str = config.get('Cookies', 'initial_cookies', fallback="")
        initial_cookies = {k.strip(): v.strip() for pair in cookies_str.split(',') if '=' in pair for k, v in [pair.split('=', 1)]}

    except Exception as e:
        logging.critical(f"Ошибка конфигурации: {e}")
        return

    # --- УСИЛЕННАЯ ВЕРСИЯ СКРЕЙПЕРА ---
    CIPHERS = (
        'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:'
        'ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:'
        'DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384'
    )
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True},
        cipherSuite=CIPHERS
    )
    if initial_cookies:
        scraper.cookies.update(initial_cookies)

    start_url = f"https://{domain}{topic_path}"

    # --- ЭТАП 1: АНАЛИЗ ---
    logging.info("--- Этап 1: Анализ индексного поста ---")
    posts_on_first_page = parse_topic_page(scraper, start_url)
    if not posts_on_first_page:
        logging.critical("Не удалось спарсить первую страницу после нескольких попыток. Выход.")
        return

    analysis_result = analyze_index_post(posts_on_first_page[0], start_url)
    if not analysis_result.prompt_links:
        logging.warning("Анализ завершен, целевых ссылок в индексном посте не найдено.")
        return

    # --- ЭТАП 2: ПАРСИНГ ---
    logging.info(f"\n--- Этап 2: Парсинг {len(analysis_result.prompt_links)} целевых постов ---")
    all_targeted_posts: List[PostData] = []
    total_links = len(analysis_result.prompt_links)
    for i, prompt in enumerate(analysis_result.prompt_links, 1):
        logging.info(f"Обработка [{i}/{total_links}]: \"{prompt.description}\"")
        single_post = parse_single_post_by_url(scraper, prompt.url)
        if single_post:
            all_targeted_posts.append(single_post)
        if i < total_links:
            time.sleep(random.uniform(min_delay, max_delay))

    # ... (вывод итогов)
    logging.info("\n--- Итог ---")
    logging.info(f"Успешно спарсено: {len(all_targeted_posts)} из {len(analysis_result.prompt_links)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("\nПроцесс прерван пользователем.")