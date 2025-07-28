import json
import logging
import os
import random
import re
import time
from pathlib import Path
from typing import Dict, Any, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# Используем отдельный логгер для парсера
logger = logging.getLogger('SiteParser')
# Установим базовый уровень, чтобы логгер был активен до конфигурации
logger.setLevel(logging.DEBUG)


# Конфигурация логирования с уровнем из конфига
def configure_logging(config: Dict):
    """Настраивает систему логирования на основе конфигурационного файла."""
    log_level = config.get('log_level', 'INFO').upper()
    log_file = config.get('log_file', 'parsing.log')

    # Удаляем все предыдущие обработчики, чтобы избежать дублирования логов
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logger.info(f"Логирование настроено. Уровень: {log_level}, Файл: {log_file}")


class SiteParser:
    DEFAULT_HEADERS = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'DNT': '1',
        'Upgrade-Insecure-Requests': '1',
    }

    def __init__(self, config_file: str = 'parser_config.json'):
        self.script_dir = Path(__file__).parent.absolute()
        self.config_path = self.script_dir / config_file
        self.config = self.load_config()

        # Настройка логирования после загрузки конфига
        configure_logging(self.config.get('logging', {}))

        self.output_dir = self.script_dir / self.config.get('output_dir', 'output')
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.user_agent = UserAgent()
        self.session = requests.Session()
        self.data: List[Dict] = []
        self.retry_attempts = self.config.get('retry_attempts', 3)
        self.retry_delay = self.config.get('retry_delay', 1)

        logger.info(f"Инициализация парсера с конфигом: {self.config_path}")

    def load_config(self) -> Dict[str, Any]:
        """Загружает и валидирует конфигурационный файл."""
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
                site for site in config.get('sites', [])
                if site.get('enabled', True)
            ]

            return config
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON в файле {self.config_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Критическая ошибка загрузки конфига: {e}", exc_info=True)
            raise

    def get_random_headers(self, custom_headers: Dict = None) -> Dict:
        """Генерирует случайные заголовки для запроса."""
        headers = self.DEFAULT_HEADERS.copy()
        headers['User-Agent'] = self.user_agent.random

        # Приоритет: пользовательские заголовки > заголовки из конфига > дефолтные
        if self.config.get('headers'):
            headers.update(self.config['headers'])
        if custom_headers:
            headers.update(custom_headers)

        logger.debug(f"Используемые заголовки: {headers}")
        return headers

    def _retry_request(self, url: str, headers: Dict, timeout: int = 10) -> requests.Response:
        """Выполняет HTTP-запрос с несколькими попытками в случае ошибки."""
        for attempt in range(self.retry_attempts):
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
                if attempt < self.retry_attempts - 1:
                    backoff = self.retry_delay * (2 ** attempt) + random.uniform(0.1, 0.5)
                    logger.warning(
                        f"Ошибка запроса к {url} (Попытка {attempt + 1}/{self.retry_attempts}): {e}. "
                        f"Повторная попытка через {backoff:.1f} сек."
                    )
                    time.sleep(backoff)
                else:
                    logger.error(f"Превышено количество попыток для {url}: {e}")
                    raise
        raise RuntimeError("Не удалось выполнить запрос после всех попыток")

    def parse(self):
        """Основной метод, запускающий парсинг всех сайтов из конфигурации."""
        try:
            if not self.config['sites']:
                logger.warning("Нет активных сайтов для парсинга в файле конфигурации.")
                return

            for site in self.config['sites']:
                self._parse_site(site)
        except Exception as e:
            logger.critical(f"Критическая ошибка во время парсинга: {e}", exc_info=True)
        finally:
            self.save_to_json()

    def _parse_site(self, site_config: Dict):
        """Парсит один сайт согласно его конфигурации."""
        site_name = site_config.get('name', 'Unknown')
        logger.info(f"Начало парсинга сайта: {site_name}")

        base_url = site_config['url']
        custom_headers = site_config.get('headers', {})
        timeout = site_config.get('timeout', 10)

        pagination = site_config.get('pagination', {})
        if pagination.get('type') == 'url_parameter' and pagination.get('enabled', True):
            param = pagination.get('param', 'page')
            max_pages = pagination.get('max_pages', 1)
            for page in range(1, max_pages + 1):
                current_url = f"{base_url}?{param}={page}"
                self._process_page(current_url, custom_headers, site_config, base_url, timeout)
                time.sleep(random.uniform(0.5, 1.5))
        else: # Если пагинация не указана или отключена, парсим одну страницу
            self._process_page(base_url, custom_headers, site_config, base_url, timeout)

    def _process_page(self, url: str, custom_headers: Dict, site_config: Dict,
                      base_url: str, timeout: int):
        """Обрабатывает одну страницу (загружает и извлекает данные)."""
        headers = self.get_random_headers(custom_headers)
        try:
            response = self._retry_request(url, headers, timeout)
            soup = BeautifulSoup(response.content, 'html.parser')

            container_selector = site_config.get('parser_config', {}).get('container', {}).get('selector')
            if not container_selector:
                logger.error(f"Селектор контейнера не найден в конфиге для сайта '{site_config.get('name')}'.")
                return

            for container in soup.select(container_selector):
                self._parse_container(container, site_config, base_url)

        except requests.exceptions.RequestException as e:
            logger.error(f"Не удалось обработать страницу {url}: {e}", exc_info=True)

    def _parse_container(self, container: BeautifulSoup, site_config: Dict, base_url: str):
        """Извлекает данные из одного контейнера (элемента) на странице."""
        config = site_config.get('parser_config', {})
        item = {}

        logger.debug(f"Обработка контейнера...")

        for field in config.get('fields', []):
            name = field['name']
            selector = field['selector']
            field_type = field.get('type', 'text')
            required = field.get('required', False)

            elements = container.select(selector)
            if not elements:
                if required:
                    logger.error(f"Пропуск контейнера: не найдено обязательное поле '{name}' (селектор: {selector})")
                    return # Прерываем обработку этого контейнера
                else:
                    item[name] = None
                    logger.warning(f"Поле '{name}' не найдено (селектор: {selector}), установлено значение None.")
                    continue

            # Обработка в зависимости от типа поля
            element = elements[0] # Берем первый найденный элемент
            value = None
            if field_type == 'text':
                value = element.get_text(strip=True)
            elif field_type == 'href':
                value = urljoin(base_url, element.get('href', ''))
            elif field_type == 'src':
                value = urljoin(base_url, element.get('src', ''))
            elif field_type == 'list':
                value = [el.get_text(strip=True) for el in elements]
            else:
                logger.error(f"Неизвестный тип поля '{field_type}' для поля '{name}'")

            item[name] = value
            logger.debug(f"Поле '{name}': '{value}'")

        # Добавляем элемент только если он не пустой
        if item:
            self.data.append(item)
            logger.info(f"Успешно обработан и добавлен элемент: {item.get('title', 'Без заголовка')}")

    def save_to_json(self):
        """Сохраняет собранные данные в JSON файл."""
        if not self.data:
            logger.warning("Нет данных для сохранения. Файл не будет создан или изменен.")
            return

        output_file = self.output_dir / self.config.get('output_file', 'parsing_output.json')
        temp_file = output_file.with_suffix('.tmp')

        try:
            logger.info(f"Сохранение {len(self.data)} записей в файл {output_file}...")
            # Атомарная запись: сначала пишем во временный файл
            with temp_file.open('w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
            # Затем заменяем основной файл временным
            os.replace(temp_file, output_file)
            logger.info(f"Данные успешно сохранены.")
        except Exception as e:
            logger.error(f"Ошибка сохранения данных в файл: {e}", exc_info=True)
            if temp_file.exists():
                os.remove(temp_file) # Удаляем временный файл в случае ошибки

# --- ДОБАВЛЕН БЛОК ДЛЯ ЗАПУСКА ---
def main():
    """
    Основная функция для запуска парсера.
    Инициализирует парсер из файла конфигурации и запускает процесс парсинга.
    """
    try:
        # Имя файла конфигурации можно передать как аргумент, если нужно
        parser = SiteParser(config_file='parser_config.json')
        parser.parse()
    except FileNotFoundError as e:
        # Это исключение перехватывается, если parser_config.json не найден
        logging.critical(f"Критическая ошибка: Файл конфигурации не найден. {e}", exc_info=True)
    except (ValueError, json.JSONDecodeError) as e:
        # Эти исключения - при неверном формате или отсутствии полей в JSON
        logging.critical(f"Критическая ошибка: Некорректный файл конфигурации. {e}", exc_info=True)
    except Exception as e:
        # Все остальные непредвиденные ошибки
        logging.critical(f"Произошла непредвиденная ошибка во время выполнения: {e}", exc_info=True)


if __name__ == '__main__':
    # Эта часть кода выполняется только при запуске скрипта напрямую,
    # а не при его импорте в другой модуль.
    main()