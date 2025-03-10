# data/storage.py
import logging
import shutil
from pathlib import Path
from typing import List, Optional

from src.models import Prompt


class LocalStorage:
    def __init__(self, base_path: str = "prompts"):
        self.logger = logging.getLogger(__name__)
        self.storage_path = Path(base_path)
        self.storage_path.mkdir(exist_ok=True)
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_prompt(self, prompt: Prompt):
        try:
            # Формируем путь с учётом категории
            category_dir = self._get_category_dir(prompt.category)
            file_path = category_dir / f"{prompt.id}.json"

            json_data = prompt.model_dump_json(indent=2)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json_data)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения промпта {prompt.id}: {str(e)}", exc_info=True)

    def load_prompt(self, prompt_id: str) -> Optional[Prompt]:
        """Ищет промпт в корневой папке и всех категориях"""
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
            raw_data = file_path.read_bytes()
            content = raw_data.decode('utf-8', errors='replace')
            cleaned_content = content.replace('\ufffd', '').replace('\x98', '')

            # Автоматическое пересохранение при проблемах с кодировкой
            self._resave_if_needed(file_path, raw_data, cleaned_content)

            return Prompt.model_validate_json(cleaned_content)
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
        else:
            raise FileNotFoundError(f"Файл промпта {prompt_id} не найден")
