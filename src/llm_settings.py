import json
import logging
import os
import secrets
import sys
from base64 import urlsafe_b64encode, urlsafe_b64decode
from pathlib import Path
from typing import Dict, Any, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from key_encryption import KeyEncryption


class Settings:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.settings_dir = self._get_settings_dir()
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.settings_dir / 'settings.json'
        self.api_keys_file = self.settings_dir / '.keystore'
        self.key_encryption = KeyEncryption()

        # Структура настроек по умолчанию
        self.default_settings = {
            "favorites": {},  # id промпта: True/False
            "local_prompts": {},  # id промпта: True/False
            "local_updated_at": {},  # id промпта: локальное время изменения в ISO формате
            "window": {
                "size": [800, 600],
                "position": [100, 100]
            },
            "filters": {
                "last_category": "Все категории",
                "last_tag": "Все теги",
                "last_language": "Все"
            }
        }

        # Структура API ключей по умолчанию
        self.default_api_keys = {
            "huggingface": {
                "key": None,
                "salt": None
            },
            "openai": {
                "key": None,
                "salt": None
            },
            "anthropic": {
                "key": None,
                "salt": None
            }
        }

        # Загружаем настройки
        self.settings = self.load_settings()
        self.api_keys = self.load_api_keys()

    def _get_settings_dir(self) -> Path:
        """Определяет путь для хранения настроек в зависимости от ОС"""
        app_name = "AiPromptManager"

        # Проверяем переменную окружения XDG_CONFIG_HOME (для Linux)
        xdg_config = os.environ.get('XDG_CONFIG_HOME')

        if sys.platform == 'win32':
            # Windows: используем APPDATA или LOCALAPPDATA
            base_path = os.environ.get('APPDATA') or os.environ.get('LOCALAPPDATA')
            if not base_path:
                base_path = os.path.expanduser('~')
            return Path(base_path) / app_name

        elif sys.platform == 'darwin':
            # macOS: используем ~/Library/Application Support
            return Path.home() / "Library" / "Application Support" / app_name

        else:
            # Linux/Unix: используем XDG_CONFIG_HOME или ~/.config
            if xdg_config:
                return Path(xdg_config) / app_name
            return Path.home() / ".config" / app_name

    def load_settings(self) -> Dict[str, Any]:
        """Загрузка настроек из файла"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # Обновляем загруженные настройки значениями по умолчанию для отсутствующих ключей
                    settings = self.default_settings.copy()
                    settings.update(loaded_settings)
                    return settings
            else:
                # Если файл не существует, создаем его с настройками по умолчанию
                settings = self.default_settings.copy()
                try:
                    with open(self.settings_file, 'w', encoding='utf-8') as f:
                        json.dump(settings, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    self.logger.warning(f"Не удалось создать файл настроек: {str(e)}", exc_info=True)
                return settings
        except Exception as e:
            self.logger.error(f"Ошибка загрузки настроек: {str(e)}", exc_info=True)
            return self.default_settings.copy()

    def save_settings(self):
        """Сохранение настроек в файл"""
        try:
            # Убеждаемся, что директория существует
            self.settings_dir.mkdir(parents=True, exist_ok=True)

            # Сохраняем настройки
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения настроек: {str(e)}", exc_info=True)
            # Выводим дополнительную информацию для отладки
            self.logger.debug(f"Путь к файлу настроек: {self.settings_file}")
            self.logger.debug(f"Текущие настройки: {self.settings}")

    def is_favorite(self, prompt_id: str) -> bool:
        """Проверка, является ли промпт избранным"""
        return self.settings["favorites"].get(prompt_id, False)

    def set_favorite(self, prompt_id: str, is_favorite: bool):
        """Установка статуса избранного для промпта"""
        if is_favorite:
            self.settings["favorites"][prompt_id] = True
        else:
            self.settings["favorites"].pop(prompt_id, None)
        self.save_settings()

    def is_local(self, prompt_id: str) -> bool:
        """Проверка, является ли промпт локальным"""
        return self.settings["local_prompts"].get(prompt_id, False)

    def set_local(self, prompt_id: str, is_local: bool):
        """Установка статуса локального для промпта"""
        if is_local:
            self.settings["local_prompts"][prompt_id] = True
        else:
            self.settings["local_prompts"].pop(prompt_id, None)
        self.save_settings()

    def save_window_state(self, size, position):
        """Сохранение состояния окна"""
        self.settings["window"]["size"] = size
        self.settings["window"]["position"] = position
        self.save_settings()

    def get_window_state(self):
        """Получение состояния окна"""
        return (
            self.settings["window"]["size"],
            self.settings["window"]["position"]
        )

    def save_filter_state(self, category: str, tag: str, language: str):
        """Сохранение состояния фильтров"""
        self.settings["filters"]["last_category"] = category
        self.settings["filters"]["last_tag"] = tag
        self.settings["filters"]["last_language"] = language
        self.save_settings()

    def get_filter_state(self):
        """Получение состояния фильтров"""
        return (
            self.settings["filters"]["last_category"],
            self.settings["filters"]["last_tag"],
            self.settings["filters"]["last_language"]
        )

    def get_local_updated_at(self, prompt_id: str) -> str:
        """Получение локального времени изменения файла"""
        return self.settings["local_updated_at"].get(prompt_id)

    def set_local_updated_at(self, prompt_id: str, updated_at: str):
        """Установка локального времени изменения файла"""
        self.settings["local_updated_at"][prompt_id] = updated_at
        self.save_settings()

    def remove_local_updated_at(self, prompt_id: str):
        """Удаление записи о локальном времени изменения"""
        self.settings["local_updated_at"].pop(prompt_id, None)
        self.save_settings()

    def clear_local_updated_at(self):
        """Очистка всех записей о локальном времени изменения"""
        self.settings["local_updated_at"] = {}
        self.save_settings()

    def load_api_keys(self) -> Dict[str, dict]:
        """Загрузка зашифрованных API ключей из файла"""
        try:
            if self.api_keys_file.exists():
                with open(self.api_keys_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Если файл не существует, создаем его
                api_keys = self.default_api_keys.copy()
                self.save_api_keys(api_keys)
                return api_keys
        except Exception as e:
            self.logger.error(f"Ошибка загрузки API ключей: {str(e)}", exc_info=True)
            return self.default_api_keys.copy()

    def save_api_keys(self, api_keys: Dict[str, dict]):
        """Сохранение зашифрованных API ключей в файл"""
        try:
            with open(self.api_keys_file, 'w', encoding='utf-8') as f:
                json.dump(api_keys, f, indent=2)

            # Устанавливаем права доступа только для текущего пользователя
            if sys.platform != 'win32':
                self.api_keys_file.chmod(0o600)

        except Exception as e:
            self.logger.error(f"Ошибка сохранения API ключей: {str(e)}", exc_info=True)

    def _derive_master_key(self) -> bytes:
        """Получение мастер-ключа для шифрования API ключей"""
        # Получаем или создаем соль для мастер-ключа
        master_salt_file = self.settings_dir / '.master_salt'
        if not master_salt_file.exists():
            master_salt = secrets.token_bytes(32)
            with open(master_salt_file, 'wb') as f:
                f.write(master_salt)
            if sys.platform != 'win32':
                master_salt_file.chmod(0o600)
        else:
            with open(master_salt_file, 'rb') as f:
                master_salt = f.read()

        # Используем имя пользователя и путь к директории как основу для ключа
        user = os.environ.get('USERNAME') or os.environ.get('USER') or 'default'
        base = (user + str(self.settings_dir)).encode()

        # Используем Scrypt для получения ключа (более устойчив к перебору)
        kdf = Scrypt(
            salt=master_salt,
            length=32,
            n=2 ** 16,  # CPU/память параметр
            r=8,  # размер блока
            p=1,  # параллелизм
        )
        return kdf.derive(base)

    def _encrypt_key(self, key: str) -> tuple[str, str, str]:
        """Шифрование API ключа"""
        if not key:
            return None, None, None

        try:
            # Получаем мастер-ключ
            master_key = self._derive_master_key()

            # Создаем AESGCM шифровальщик
            aesgcm = AESGCM(master_key)

            # Генерируем случайные соль и nonce
            salt = secrets.token_bytes(16)
            nonce = secrets.token_bytes(12)

            # Шифруем ключ
            key_bytes = key.encode()
            encrypted_key = aesgcm.encrypt(nonce, key_bytes, None)

            # Кодируем в base64 для хранения
            return (
                urlsafe_b64encode(encrypted_key).decode(),
                urlsafe_b64encode(salt).decode(),
                urlsafe_b64encode(nonce).decode()
            )
        except Exception as e:
            self.logger.error(f"Ошибка шифрования ключа: {str(e)}", exc_info=True)
            raise

    def _decrypt_key(self, encrypted_key: str, salt: str, nonce: str) -> Optional[str]:
        """Расшифровка API ключа"""
        if not all([encrypted_key, salt, nonce]):
            return None

        try:
            # Получаем мастер-ключ
            master_key = self._derive_master_key()

            # Создаем AESGCM дешифровщик
            aesgcm = AESGCM(master_key)

            # Декодируем из base64
            encrypted_bytes = urlsafe_b64decode(encrypted_key)
            nonce_bytes = urlsafe_b64decode(nonce)

            # Расшифровываем ключ
            decrypted_key = aesgcm.decrypt(nonce_bytes, encrypted_bytes, None)
            return decrypted_key.decode()

        except Exception as e:
            self.logger.error(f"Ошибка расшифровки ключа: {str(e)}", exc_info=True)
            return None

    def get_api_key(self, service: str) -> Optional[str]:
        """Получение API ключа для сервиса"""
        try:
            service_data = self.api_keys.get(service, {})
            if not service_data or not service_data.get("key"):
                return None

            encrypted_key = service_data.get("key")
            salt = service_data.get("salt")
            nonce = service_data.get("nonce")

            return self._decrypt_key(encrypted_key, salt, nonce)

        except Exception as e:
            self.logger.error(f"Ошибка получения API ключа: {str(e)}", exc_info=True)
            return None

    def set_api_key(self, service: str, key: str):
        """Установка API ключа для сервиса"""
        try:
            if not key:
                self.remove_api_key(service)
                return

            # Шифруем ключ
            encrypted_key, salt, nonce = self._encrypt_key(key)

            # Сохраняем зашифрованный ключ и метаданные
            self.api_keys[service] = {
                "key": encrypted_key,
                "salt": salt,
                "nonce": nonce
            }

            self.save_api_keys(self.api_keys)

        except Exception as e:
            self.logger.error(f"Ошибка установки API ключа: {str(e)}", exc_info=True)
            raise

    def remove_api_key(self, service: str):
        """Удаление API ключа"""
        if service in self.api_keys:
            self.api_keys[service] = {
                "key": None,
                "salt": None
            }
            self.save_api_keys(self.api_keys)

    def get_config_path(self, filename: str) -> str:
        """
        Получает путь к файлу конфигурации
        
        Args:
            filename: Имя файла конфигурации
            
        Returns:
            str: Полный путь к файлу конфигурации
        """
        return str(self.settings_dir / filename)
