# data/storage.py
import json
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from src.models import Prompt
from src.settings import Settings


class DateTimeEncoder(json.JSONEncoder):
    """Кастомный JSON энкодер для обработки datetime объектов"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class LocalStorage:
    def __init__(self, base_path: str = "prompts"):
        self.logger = logging.getLogger(__name__)
        self.storage_path = Path(base_path)
        self.storage_path.mkdir(exist_ok=True)
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.settings = Settings()

    def save_prompt(self, prompt: Prompt):
        try:
            # Сохраняем локальные настройки
            self.settings.set_local(prompt.id, bool(prompt.is_local))
            self.settings.set_favorite(prompt.id, bool(prompt.is_favorite))

            # Сохраняем локальное время изменения
            current_time = datetime.now().isoformat()
            self.settings.set_local_updated_at(prompt.id, current_time)

            # Устанавливаем флаги в False перед сохранением
            prompt_dict = prompt.model_dump()
            prompt_dict["is_local"] = bool(False)
            prompt_dict["is_favorite"] = bool(False)

            # Проверяем и устанавливаем категорию
            if not prompt_dict.get("category"):
                prompt_dict["category"] = "general"

            # Формируем путь с учётом категории
            category_dir = self._get_category_dir(prompt_dict["category"])
            file_path = category_dir / f"{prompt.id}.json"

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(prompt_dict, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)

        except Exception as e:
            self.logger.error(f"Ошибка сохранения промпта {prompt.id}: {str(e)}", exc_info=True)
            raise

    def load_prompt(self, prompt_id: str) -> Optional[Prompt]:
        """Ищет промпт в корневой папке и всех категориях"""
        prompt = self._load_prompt_base(prompt_id)
        if prompt:
            # Добавляем локальные настройки
            prompt.is_local = self.settings.is_local(prompt_id)
            prompt.is_favorite = self.settings.is_favorite(prompt_id)
            
            # updated_at остается как есть из файла промпта
            # Оно будет обновляться только при синхронизации с сервера
        return prompt

    def _load_prompt_base(self, prompt_id: str) -> Optional[Prompt]:
        """Базовая загрузка промпта без локальных настроек"""
        # Сначала проверяем корневую папку (для случаев без категорий)
        root_file = self.storage_path / f"{prompt_id}.json"
        if root_file.exists():
            return self._load_from_path(root_file)

        # Затем проверяем все подпапки (категории)
        for category_dir in self.storage_path.iterdir():
            if category_dir.is_dir():
                file_path = category_dir / f"{prompt_id}.json"
                if file_path.exists():
                    return self._load_from_path(file_path)

        return None

    def _load_from_path(self, file_path: Path) -> Optional[Prompt]:
        """Вспомогательный метод для загрузки и очистки данных"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Проверяем и устанавливаем категорию
            if not data.get("category"):
                data["category"] = "general"
                
            # Конвертируем строки ISO в datetime
            if "created_at" in data and isinstance(data["created_at"], str):
                data["created_at"] = datetime.fromisoformat(data["created_at"])
            if "updated_at" in data and isinstance(data["updated_at"], str):
                data["updated_at"] = datetime.fromisoformat(data["updated_at"])

            return Prompt.model_validate(data)
        except Exception as e:
            self.logger.error(f"Ошибка загрузки {file_path.name}: {str(e)}")
            return None

    def list_prompts(self) -> List[Prompt]:
        prompts = []
        # Ищем в корне (для совместимости с существующими файлами)
        for file_path in self.storage_path.glob("*.json"):
            if not file_path.is_dir():
                try:
                    prompt = self.load_prompt(file_path.stem)
                    if prompt:
                        # Проверяем категорию
                        if not prompt.category:
                            prompt.category = "general"
                        prompts.append(prompt)
                except Exception as e:
                    self.logger.error(f"Ошибка чтения {file_path.name}: {str(e)}")

        # Ищем во всех категориях
        for category_dir in self.storage_path.iterdir():
            if category_dir.is_dir():
                for file_path in category_dir.glob("*.json"):
                    try:
                        prompt = self.load_prompt(file_path.stem)
                        if prompt:
                            # Проверяем и устанавливаем категорию из пути
                            if not prompt.category or prompt.category != category_dir.name:
                                prompt.category = category_dir.name
                            prompts.append(prompt)
                    except Exception as e:
                        self.logger.error(f"Ошибка чтения {file_path.name}: {str(e)}")
        return prompts

    def _resave_if_needed(self, file_path: Path, original_data: bytes, cleaned_content: str):
        """Пересохраняет файл, если обнаружены проблемы с кодировкой"""
        try:
            # Сравниваем оригинальные данные с очищенными
            if original_data != cleaned_content.encode('utf-8'):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                self.logger.info(f"Файл {file_path.name} автоматически пересохранен в UTF-8")
        except Exception as e:
            self.logger.warning(f"Не удалось пересохранить {file_path.name}: {str(e)}")

    def _get_category_dir(self, category: str) -> Path:
        """Возвращает путь к категории, создавая её при необходимости"""
        category_dir = self.storage_path / category
        category_dir.mkdir(parents=True, exist_ok=True)
        return category_dir

    def move_prompt_file(self, prompt_id: str, old_category: str, new_category: str):
        """Перемещает файл промпта между категориями"""
        old_path = self._get_category_dir(old_category) / f"{prompt_id}.json"
        new_path = self._get_category_dir(new_category) / f"{prompt_id}.json"

        # Если файл в старой категории не найден — ищем в корне
        if not old_path.exists():
            old_path = self.storage_path / f"{prompt_id}.json"  # Корневая папка

        if old_path.exists():
            old_path.rename(new_path)
        else:
            raise ValueError(
                f"Файл промпта {prompt_id} не найден в категории {old_category} или в корне")

    def delete_prompt(self, prompt_id: str, category: str = None):
        """Удаляет промпт по ID, категория определяется из промпта или передаётся явно"""
        if not category:
            prompt = self.load_prompt(prompt_id)
            if not prompt:
                raise ValueError("Промпт не найден")
            category = prompt.category

        category_dir = self._get_category_dir(category)
        file_path = category_dir / f"{prompt_id}.json"

        if file_path.exists():
            file_path.unlink()
            # Удаляем информацию о локальном времени изменения
            self.settings.remove_local_updated_at(prompt_id)
        else:
            raise FileNotFoundError(f"Файл промпта {prompt_id} не найден")
