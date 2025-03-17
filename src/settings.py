import json
import logging
from pathlib import Path
import os
import sys
from typing import Dict, Any

class Settings:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.settings_dir = self._get_settings_dir()
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.settings_dir / 'settings.json'
        
        # Структура настроек по умолчанию
        self.default_settings = {
            "favorites": {},  # id промпта: True/False
            "local_prompts": {},  # id промпта: True/False
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
        
        # Загружаем настройки
        self.settings = self.load_settings()

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
                    return json.load(f)
            return self.default_settings.copy()
        except Exception as e:
            self.logger.error(f"Ошибка загрузки настроек: {str(e)}", exc_info=True)
            return self.default_settings.copy()

    def save_settings(self):
        """Сохранение настроек в файл"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения настроек: {str(e)}", exc_info=True)

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