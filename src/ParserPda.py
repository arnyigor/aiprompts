from pathlib import Path

import cloudscraper
import re
import time
import random
import configparser
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple, Any

def parse_topic_page(url: str, domain: str, initial_cookies: Dict[str, str]) -> Optional[Tuple[int, List[Dict[str, Any]], Optional[str]]]:
    """
    Парсит ОДНУ страницу темы.
    """
    print(f"[*] Парсим страницу: {url}")
    scraper = cloudscraper.create_scraper()
    try:
        # --- ИЗМЕНЕНИЕ: Устанавливаем cookie из конфига ---
        print(f"  [i] Устанавливаем начальные cookie: {initial_cookies}")
        for name, value in initial_cookies.items():
            scraper.cookies.set(name, value, domain=domain)
        # ---------------------------------------------------

        response = scraper.get(url, timeout=20)
        response.raise_for_status()
        response.encoding = 'windows-1251'

        soup = BeautifulSoup(response.text, 'lxml')

        # ... остальной код функции parse_topic_page без изменений ...
        page_num_element = soup.find('span', class_='pagecurrent-wa')
        current_page = int(page_num_element.text.strip()) if page_num_element else 1
        next_page_url = None
        next_page_element = soup.find('a', title='Следующая страница')
        if next_page_element and next_page_element.has_attr('href'):
            next_page_url = next_page_element['href']
        post_elements = soup.find_all('table', attrs={'data-post': True})
        if not post_elements:
            return current_page, [], next_page_url
        extracted_posts = []
        for post_table in post_elements:
            author_element = post_table.find('span', class_='normalname')
            author = author_element.text.strip() if author_element else "Неизвестный автор"
            content_element = post_table.find('div', class_='postcolor')
            content_text = content_element.get_text(separator='\n', strip=True) if content_element else ""
            date_str = "Дата не найдена"
            date_cells = post_table.find_all('td', class_='row2')
            if len(date_cells) > 1:
                match = re.search(r'\d{2}\.\d{2}\.\d{2}, \d{2}:\d{2}', date_cells[1].get_text())
                if match:
                    date_str = match.group(0)
            extracted_posts.append({
                'author': author,
                'content': content_text,
                'date': date_str,
                'page': current_page
            })
        return current_page, extracted_posts, next_page_url

    except Exception as e:
        print(f"  [✗] Произошла ошибка при загрузке или парсинге страницы {url}: {e}")
        return None

def crawl_topic(start_url: str, domain: str, initial_cookies: Dict[str, str], max_pages: Optional[int] = None, delay_range: Tuple[float, float] = (1.5, 3.5)):
    all_posts = []
    current_url: Optional[str] = start_url
    pages_processed = 0
    while current_url:
        if max_pages and pages_processed >= max_pages:
            print(f"\n[!] Достигнут лимит в {max_pages} страниц. Остановка.")
            break

        result = parse_topic_page(current_url, domain, initial_cookies)

        if not result:
            print("[!] Не удалось обработать страницу. Остановка.")
            break

        page_num, posts_on_page, next_url = result
        if posts_on_page:
            print(f"  [+] Со страницы {page_num} извлечено {len(posts_on_page)} постов.")
            all_posts.extend(posts_on_page)

        current_url = next_url
        pages_processed += 1

        if current_url:
            min_delay, max_delay = delay_range
            random_delay = random.uniform(min_delay, max_delay)
            print(f"  [->] Следующая страница: {current_url}")
            print(f"  ...Пауза на {random_delay:.2f} секунд...")
            time.sleep(random_delay)
        else:
            print("\n[✓] Достигнута последняя страница. Парсинг завершен.")
    return all_posts


if __name__ == "__main__":
    # --- ИЗМЕНЕНИЕ: Строим надежный путь к файлу ---
    try:
        # Путь к текущему файлу скрипта (parser_script.py)
        current_script_path = Path(__file__).resolve()
        # Путь к корневой папке проекта (на один уровень выше папки 'src')
        project_root = current_script_path.parent.parent
        # Полный путь к файлу config.ini
        config_path = project_root / 'config.ini'

        print(f"[*] Ищем файл конфигурации по пути: {config_path}")

        config = configparser.ConfigParser()
        # Читаем конфиг по полному пути
        read_files = config.read(config_path, encoding='utf-8-sig')

        if not read_files:
            raise FileNotFoundError(f"Файл конфигурации не найден по пути: {config_path}")

        # Извлекаем данные из конфига
        DOMAIN = config.get('Target', 'domain')
        TOPIC_PATH = config.get('Target', 'topic_path')

        MAX_PAGES = config.getint('ParserSettings', 'max_pages_to_crawl')
        MIN_DELAY = config.getfloat('ParserSettings', 'min_delay_seconds')
        MAX_DELAY = config.getfloat('ParserSettings', 'max_delay_seconds')

        cookies_str = config.get('Cookies', 'initial_cookies', fallback="")
        INITIAL_COOKIES = {}
        if cookies_str:
            pairs = cookies_str.split(',')
            for pair in pairs:
                if '=' in pair:
                    key, value = pair.strip().split('=', 1)
                    INITIAL_COOKIES[key] = value

    except FileNotFoundError as e:
        print(f"[✗] Критическая ошибка: {e}")
        exit()
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        print(f"[✗] Ошибка в файле config.ini: {e}")
        exit()
    # ----------------------------------------------------

    start_url = f"https://{DOMAIN}{TOPIC_PATH}"

    print("--- Запускаем парсинг темы с умной задержкой (настройки из config.ini) ---")
    all_collected_posts = crawl_topic(
        start_url=start_url,
        domain=DOMAIN,
        initial_cookies=INITIAL_COOKIES, # Передаем словарь с cookie
        max_pages=MAX_PAGES,
        delay_range=(MIN_DELAY, MAX_DELAY)
    )

    if all_collected_posts:
        print(f"\n--- Итог ---")
        print(f"Всего собрано постов: {len(all_collected_posts)}")
        # ... (остальной код для вывода результатов)
