import json
import logging
import time
from pathlib import Path
from random import random
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('parsing.log'),
        logging.StreamHandler()
    ]
)


class SiteParser:
    DEFAULT_HEADERS = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'DNT': '1',
        'Upgrade-Insecure-Requests': '1',
    }

    def __init__(self, config_file='parser_config.json'):
        self.script_dir = Path(__file__).parent.absolute()
        self.config_path = self.script_dir / config_file
        self.output_dir = self.script_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = self.load_config()
        self.data = []
        self.user_agent = UserAgent()

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.output_dir / 'parsing.log'),
                logging.StreamHandler()
            ]
        )

        logging.info(f"Инициализация парсера с конфигом: {self.config_path}")

    def load_config(self):
        """Загрузка конфигурации с проверкой"""
        try:
            if not self.config_path.exists():
                error_msg = f"Файл конфигурации не найден: {self.config_path}"
                logging.error(error_msg)
                raise FileNotFoundError(error_msg)

            config = json.loads(self.config_path.read_text(encoding='utf-8'))

            # Фильтрация активных сайтов
            active_sites = []
            for site in config.get('sites', []):
                if site.get('enabled', True):
                    active_sites.append(site)
                else:
                    logging.debug(f"Шаблон {site.get('name')} пропущен (enabled=False)")

            config['sites'] = active_sites
            return config
        except Exception as e:
            error_msg = f"Ошибка при загрузке конфига: {str(e)}"
            logging.error(error_msg)
            raise ValueError(error_msg)

    def get_random_headers(self, custom_headers=None):
        """Генерация случайных заголовков"""
        headers = self.DEFAULT_HEADERS.copy()
        headers['User-Agent'] = self.user_agent.random

        # Добавляем кастомные заголовки из конфига
        if self.config.get('headers'):
            headers.update(self.config['headers'])

        # Добавляем пользовательские заголовки
        if custom_headers:
            headers.update(custom_headers)

        logging.debug(f"Используемые заголовки: {headers}")
        return headers

    def parse(self):
        """Основной метод парсинга"""
        try:
            for site_config in self.config.get('sites', []):
                self._parse_site(site_config)
        except Exception as e:
            logging.error(f"Критическая ошибка парсинга: {e}", exc_info=True)
            raise
        finally:
            self.save_to_json()

    def _parse_site(self, site_config):
        """Парсинг отдельного сайта"""
        site_name = site_config.get('name', 'Unknown')
        logging.info(f"Начат парсинг сайта: {site_name}")

        try:
            base_url = site_config['url']
            custom_headers = site_config.get('headers', {})

            # Обработка пагинации
            pagination = site_config.get('pagination', {})
            if pagination.get('type') == 'url_parameter':
                for page in range(1, pagination['max_pages'] + 1):
                    current_url = f"{base_url}?{pagination['param']}={page}"
                    headers = self.get_random_headers(custom_headers)
                    self._process_page(current_url, headers, site_config, base_url)
                    time.sleep(random.uniform(0.5, 1.5))
            else:
                headers = self.get_random_headers(custom_headers)
                self._process_page(base_url, headers, site_config, base_url)

        except Exception as e:
            logging.error(f"Ошибка при парсинге сайта {site_name}: {e}", exc_info=True)
            raise

    def _process_page(self, url, headers, site_config, base_url):
        """Обработка отдельной страницы"""
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Парсинг контейнера
            container_selector = site_config.get('container_selector')
            if container_selector:
                containers = soup.select(container_selector)
                logging.debug(
                    f"Найдено {len(containers)} элементов по селектору {container_selector}")
                for container in containers:
                    self._parse_container(container, site_config, base_url)
            else:
                self._parse_container(soup, site_config, base_url)

        except requests.exceptions.RequestException as e:
            logging.error(f"Ошибка запроса к {url}: {e}")
            raise

    def _parse_container(self, container, site_config, base_url):
        """Парсинг элемента контейнера с поддержкой вложенных структур"""
        item = {}
        # 1. Парсим основные поля
        for key, selector in site_config.get('item_selectors', {}).items():
            try:
                element = container.select_one(selector)
                item[key] = self._process_element(element, key, base_url)
                logging.debug(f"Спарсено поле '{key}': {item[key]}")
            except Exception as e:
                logging.warning(f"Ошибка парсинга поля {key} с селектором {selector}: {e}")

        # 2. Парсим детали (если есть ссылка)
        if 'details_link' in item and site_config.get('details'):
            details_url = item['details_link']
            logging.info(f"Переход на детальную страницу: {details_url}")
            details_data = self._parse_details_page(details_url, site_config['details'])
            item.update(details_data)

        self.data.append(item)

    def _parse_details_page(self, url, details_config):
        """Парсинг детальной страницы с вложенными списками"""
        headers = self.get_random_headers()
        details = {}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # 1. Парсим основные поля детальной страницы
            for key, selector in details_config.get('content_selectors', {}).items():
                element = soup.select_one(selector)
                details[key] = self._process_element(element, key, url)
                logging.debug(f"Спарсено детальное поле '{key}': {details[key]}")

            # 2. Парсим вложенные списки
            for nested_list in details_config.get('nested_lists', []):
                list_name = nested_list['name']
                details[list_name] = []
                container = soup.select_one(nested_list['container'])

                if container:
                    items = container.select(nested_list['item_selector'])
                    for sub_item in items:
                        sub_data = {}
                        for key, selector in nested_list['selectors'].items():
                            element = sub_item.select_one(selector)
                            sub_data[key] = self._process_element(element, key, url)
                        details[list_name].append(sub_data)
                else:
                    logging.warning(f"Контейнер {nested_list['container']} не найден на {url}")

        except requests.exceptions.RequestException as e:
            logging.error(f"Ошибка при парсинге детальной страницы {url}: {e}")
            return {}

        return details

    def _process_element(self, element, key, base_url):
        """Обработка элемента"""
        if not element:
            return None
        if 'link' in key:
            return urljoin(base_url, element.get('href', ''))
        if 'image' in key:
            return urljoin(base_url, element.get('src', ''))
        return element.get_text(strip=True)

    def save_to_json(self):
        """Сохранение результата"""
        output_file = self.output_dir / 'parsing_output.json'
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            logging.info(f"Данные успешно сохранены в {output_file}")
        except Exception as e:
            logging.error(f"Ошибка сохранения файла: {e}")
            raise
