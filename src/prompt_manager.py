import json
import logging
import string
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from src.category_manager import CategoryManager
from src.models import Prompt
from src.storage import LocalStorage


class PromptManager:
    prompts: dict[string, Prompt]

    def __init__(self, storage_path="prompts"):
        self.logger = logging.getLogger(__name__)
        self.cat_manager = CategoryManager()
        self.storage = LocalStorage(storage_path)
        self.prompts = {p.id: p for p in self.storage.list_prompts()}
        self.storage_path = Path(storage_path)
        self.load_all_prompts()

    def load_all_prompts(self):
        """Загрузка всех промптов в кэш при старте"""
        for prompt in self.storage.list_prompts():
            self.prompts[prompt.id] = prompt
        self.logger.info(f"Загружено {len(self.prompts)} промптов")

    def list_prompts(self) -> list[Prompt]:
        """Загружает промпты в кэш при первом вызове"""
        return list(self.prompts.values())

    def get_prompt(self, prompt_id: str) -> Optional[Prompt]:
        """Интерфейсный метод для получения промпта"""
        return self.storage.load_prompt(prompt_id)

    def is_in_category_tree(self, child_code: str, parent_code: str) -> bool:
        current = self.cat_manager.get_category(child_code)
        while current.parent:
            if current.parent == parent_code:
                return True
            current = self.cat_manager.get_category(current.parent)
        return False

    def search_prompts(self, query: str, category: str = None) -> list[Prompt]:
        results = []
        for prompt in self.prompts.values():
            # Извлекаем текст из контента
            content_text = " ".join(str(v) for v in prompt.content.values())  # Объединяем все языки
            # Проверяем все поля
            if (query.lower() in prompt.title.lower() or
                    query.lower() in prompt.description.lower() or
                    query.lower() in content_text.lower()):
                if not category or self.is_in_category_tree(prompt.category, category):
                    results.append(prompt)
        return results

    def validate_unique(self, prompt_id):
        if prompt_id in self.prompts:
            raise ValueError(f"Prompt с ID {prompt_id} уже существует")

    def add_prompt(self, prompt_data: dict):
        # Автоматически добавляем временные метки, если их нет
        self.logger.debug("Добавление промпта: %s", prompt_data)
        # Генерируем id, если его нет
        if 'id' not in prompt_data:
            prompt_data['id'] = str(uuid4())
        prompt_data.setdefault('created_at', datetime.utcnow())
        prompt_data.setdefault('updated_at', datetime.utcnow())
        prompt = Prompt(**prompt_data)
        self.validate_unique(prompt.id)
        self.prompts[prompt.id] = prompt
        self.storage.save_prompt(prompt)

    def edit_prompt(self, prompt_id: str, new_data: dict):
        self.logger.debug(f"Редактирование промпта {prompt_id} с данными: {new_data}")
        if prompt_id not in self.prompts:
            raise ValueError("Prompt не найден")

        updated_data = self.prompts[prompt_id].model_dump()
        updated_data.update(new_data)
        updated_prompt = Prompt(**updated_data)

        self.prompts[prompt_id] = updated_prompt
        self.storage.save_prompt(updated_prompt)

    def delete_prompt(self, prompt_id: str):
        self.logger.warning(f"Удаление промпта {prompt_id}")
        file_path = self.storage.storage_path / f"{prompt_id}.json"
        if file_path.exists():
            file_path.unlink()
        if prompt_id in self.prompts:
            del self.prompts[prompt_id]

    def get_prompt_history(self, prompt_id: str):
        """Получение истории версий промпта"""
        versions_dir = self.storage_path / "versions" / prompt_id
        if not versions_dir.exists():
            return []

        return sorted(
            versions_dir.glob("*.json"),
            key=lambda p: p.stem,
            reverse=True
        )

    def rollback_prompt(self, prompt_id: str, version_timestamp: str):
        """Откат к определенной версии"""
        versions_dir = self.storage_path / "versions" / prompt_id
        version_file = versions_dir / f"{version_timestamp}.json"

        if not version_file.exists():
            raise FileNotFoundError("Версия не найдена")

        with open(version_file, 'r') as f:
            data = json.load(f)
            self.edit_prompt(prompt_id, data)
