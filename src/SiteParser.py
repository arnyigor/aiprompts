import json
import logging
import os
import random
import re
import time
from pathlib import Path
from typing import Dict, Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# Используем отдельный логгер для парсера
logger = logging.getLogger('SiteParser')
logger.setLevel(logging.DEBUG)


# Конфигурация логирования с уровнем из конфига
def configure_logging(config):
    handlers = [
        logging.FileHandler(config.get('log_file', 'parsing.log')),
        logging.StreamHandler()
    ]
    logging.basicConfig(
        level=config.get('log_level', 'DEBUG'),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
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
        self.config = self.load_config()
        configure_logging(self.config.get('logging', {}))

        self.output_dir = self.script_dir / self.config.get('output_dir', 'output')
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.user_agent = UserAgent()
        self.session = requests.Session()
        self.data = []
        self.retry_attempts = self.config.get('retry_attempts', 3)
        self.retry_delay = self.config.get('retry_delay', 1)

        logger.info(f"Инициализация парсера с конфигом: {self.config_path}")

    def load_config(self) -> Dict[str, Any]:
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Файл конфига не найден: {self.config_path}")

            config = json.loads(self.config_path.read_text(encoding='utf-8'))

            # Валидация обязательных полей
            required = ['logging', 'output_dir', 'sites']
            for field in required:
                if field not in config:
                    raise ValueError(f"Отсутствует обязательное поле в конфиге: {field}")

            # Фильтрация активных сайтов
            config['sites'] = [
                site for site in config['sites']
                if site.get('enabled', True)
            ]

            return config
        except Exception as e:
            logger.error(f"Ошибка загрузки конфига: {str(e)}", exc_info=True)
            raise

    def get_random_headers(self, custom_headers: Dict = None) -> Dict:
        headers = self.DEFAULT_HEADERS.copy()
        headers['User-Agent'] = self.user_agent.random

        # Приоритет: пользовательские заголовки > конфига > дефолтные
        if self.config.get('headers'):
            headers.update(self.config['headers'])
        if custom_headers:
            headers.update(custom_headers)

        logger.debug(f"Используемые заголовки: {headers}")
        return headers

    def _retry_request(self, url: str, headers: Dict, timeout: int = 10) -> requests.Response:
        for attempt in range(self.retry_attempts + 1):
            try:
                response = self.session.get(
                    url,
                    headers=headers,
                    timeout=timeout,
                    allow_redirects=True
                )
                response.raise_for_status()
                logger.debug(f"Успех: {url} (Статус: {response.status_code})")
                return response
            except requests.exceptions.RequestException as e:
                if attempt < self.retry_attempts:
                    backoff = self.retry_delay * (2 ** attempt) + random.uniform(0.1, 0.5)
                    logger.warning(
                        f"Ошибка запроса к {url} (Попытка {attempt + 1}/{self.retry_attempts}): {e}. "
                        f"Повторная попытка через {backoff:.1f} сек."
                    )
                    time.sleep(backoff)
                else:
                    logger.error(f"Превышено количество попыток для {url}: {e}")
                    raise
        return None  # Не должно достигаться из-за raise выше

    def parse(self):
        try:
            for site in self.config['sites']:
                self._parse_site(site)
        except Exception as e:
            logger.error(f"Критическая ошибка парсинга: {e}", exc_info=True)
            raise
        finally:
            self.save_to_json()

    def _parse_site(self, site_config: Dict):
        site_name = site_config.get('name', 'Unknown')
        logger.info(f"Начало парсинга: {site_name}")

        base_url = site_config['url']
        custom_headers = site_config.get('headers', {})
        timeout = site_config.get('timeout', 10)

        # Поддержка разных типов пагинации
        pagination = site_config.get('pagination', {})
        if pagination.get('type') == 'url_parameter':
            param = pagination.get('param', 'page')
            max_pages = pagination.get('max_pages', 1)
            for page in range(1, max_pages + 1):
                current_url = f"{base_url}?{param}={page}"
                self._process_pagination_page(current_url, custom_headers, site_config, base_url,
                                              timeout)
                time.sleep(random.uniform(0.5, 1.5))
        elif pagination.get('type') == 'next_page_link':
            next_url = base_url
            while next_url:
                self._process_pagination_page(next_url, custom_headers, site_config, base_url,
                                              timeout)
                next_url = self._find_next_page_link(next_url, site_config)
                time.sleep(random.uniform(0.5, 1.5))
        else:
            self._process_pagination_page(base_url, custom_headers, site_config, base_url, timeout)

    def _process_pagination_page(self, url: str, custom_headers: Dict, site_config: Dict,
                                 base_url: str, timeout: int):
        headers = self.get_random_headers(custom_headers)
        try:
            response = self._retry_request(url, headers, timeout)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Извлекаем селектор контейнера из parser_config
            container_selector = site_config.get('parser_config', {}).get('container', {}).get(
                'selector')
            if not container_selector:
                logger.error("Селектор контейнера не найден в конфиге")
                return

            containers = soup.select(container_selector)
            if site_config.get('parser_config', {}).get('container', {}).get('pair_processing',
                                                                             False):
                # Обработка парами: заголовок + текст
                for i in range(0, len(containers), 2):
                    title_container = containers[i]
                    text_container = containers[i + 1] if i + 1 < len(containers) else None

                    item = {}
                    # Заголовок
                    title_elem = title_container.select_one(
                        site_config['parser_config']['fields'][0]['selector'])
                    item["title"] = title_elem.text.strip() if title_elem else None

                    # Текст
                    if text_container:
                        text_elem = text_container.select_one(
                            site_config['parser_config']['fields'][1]['selector'])
                        item["text"] = text_elem.text.strip() if text_elem else None
                    else:
                        item["text"] = None

                    self.data.append(item)
            else:
                # Обработка каждого контейнера отдельно
                for container in containers:
                    self._parse_container(container, site_config, base_url)

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при обработке страницы {url}: {e}", exc_info=True)
            raise

    def _find_next_page_link(self, current_url: str, site_config: Dict) -> str:
        next_link_selector = site_config.get('pagination', {}).get('next_link_selector')
        if not next_link_selector:
            return None

        response = self._retry_request(current_url, self.get_random_headers())
        soup = BeautifulSoup(response.content, 'html.parser')
        next_link = soup.select_one(next_link_selector)
        return urljoin(current_url, next_link.get('href', '')) if next_link else None

    def _parse_container(self, container, site_config: Dict, base_url: str):
        config = site_config.get('parser_config', {})
        item = {}

        # Логирование начала обработки контейнера
        logger.debug(
            f"Обрабатывается контейнер: {container.prettify()[:500]}..."
        )  # Ограничиваем вывод HTML

        for field in config.get('fields', []):
            name = field['name']
            selector = field['selector']
            field_type = field.get('type', 'text')
            regex = field.get('regex')
            attr = field.get('attr', '')
            required = field.get('required', False)

            # Логирование начала обработки поля
            logger.debug(f"Обработка поля '{name}':")
            logger.debug(f"  Селектор: {selector}")

            elements = container.select(selector)
            if not elements:
                if required:
                    logger.error(
                        f"Пропуск контейнера: не найдено required поле '{name}' (селектор {selector})"
                    )
                    return {}
                else:
                    item[name] = None
                    logger.warning(
                        f"Поле '{name}' не найдено (селектор {selector}), установлено значение None"
                    )
                    continue

            # Логирование найденных элементов
            logger.debug(f"  Найдено {len(elements)} элементов")

            if field_type == 'text':
                text = elements[0].get_text(strip=True)
                if regex:
                    text = re.sub(regex, '', text)
                item[name] = text
                logger.debug(f"  Результат: {text}")
            elif field_type == 'list':
                item[name] = [e.get_text(strip=True) for e in elements]
                logger.debug(f"  Результат: {item[name]}")
            elif field_type in ['href', 'src']:
                item[name] = elements[0].get(attr, '')
                logger.debug(f"  Результат: {item[name]}")
            else:
                logger.error(
                    f"Неизвестный тип поля '{field_type}' для поля '{name}'",
                    exc_info=True
                )
                item[name] = None

        # Логирование успешного парсинга элемента
        logger.info(f"Успешно обработан элемент: {item}")

        # Обработка деталей
        if config.get('details', {}).get('enabled'):
            follow_link_field = config['details'].get('follow_link')
            details_link = item.get(follow_link_field)
            if details_link:
                details_url = urljoin(base_url, details_link)
                logger.info(f"Переход на детальную страницу: {details_url}")
                details_data = self._parse_details_page(
                    details_url,
                    config['details'],
                    base_url
                )
                item.update(details_data)
            else:
                logger.warning(
                    f"Не найдена ссылка для детальной страницы в поле '{follow_link_field}'"
                )

        # Добавление в данные и логирование
        self.data.append(item)
        logger.debug(f"Добавлен элемент в данные: {item}")

    def _parse_details_page(self, url: str, details_config: Dict, base_url: str) -> Dict:
        headers = self.get_random_headers()
        details = {}  # Инициализируем пустой словарь

        try:
            response = self._retry_request(url, headers)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Обработка основных полей
            content_selectors = details_config.get('content_selectors', {})
            for key, selector in content_selectors.items():
                element = soup.select_one(selector)
                details[key] = self._process_element(element, key, base_url)

            # Обработка вложенных списков
            for nested in details_config.get('nested_lists', []):
                list_name = nested['name']
                details[list_name] = []
                container = soup.select_one(nested['container'])
                if container:
                    items = container.select(nested['item_selector'])
                    for sub_item in items:
                        sub_data = {}
                        for key, selector in nested['selectors'].items():
                            elem = sub_item.select_one(selector)
                            sub_data[key] = self._process_element(elem, key, url)
                        details[list_name].append(sub_data)
                else:
                    logger.warning(f"Контейнер {nested['container']} не найден на {url}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка парсинга детальной страницы {url}: {e}")
            return {}  # Возвращаем пустой словарь, а не None

        return details  # Всегда возвращаем словарь

    def _process_element(self, element, key: str, base_url: str) -> Any:
        if not element:
            return None
        if 'link' in key:
            return urljoin(base_url, element.get('href', ''))
        if 'image' in key:
            return urljoin(base_url, element.get('src', ''))
        return element.get_text(strip=True).strip()

    def save_to_json(self):
        output_file = self.output_dir / self.config.get('output_file', 'parsing_output.json')
        temp_file = output_file.with_suffix('.tmp')

        try:
            if not self.data:
                logger.warning("Нет данных для сохранения")
                return

            logger.debug(f"Сохраняем {len(self.data)} записей")  # Отладочный лог
            # Запись во временный файл
            with temp_file.open('w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)

            # Атомарное замещение файла (работает в Windows/Linux)
            os.replace(str(temp_file), str(output_file))

            logger.info(f"Данные сохранены в {output_file}")
        except Exception as e:
            logger.error(f"Ошибка сохранения данных: {e}")
            raise
