import json
import logging
import string
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from uuid import uuid4

from models import Prompt
from src.models import Prompt
from storage import LocalStorage


class PromptManager:
    prompts: dict[string, Prompt]

    def __init__(self, storage_path="prompts"):
        self.logger = logging.getLogger(__name__)
        self.storage = LocalStorage(storage_path)
        self.prompts = {}  # Кэш промптов
        self.storage_path = Path(storage_path)

    def list_prompts(self) -> list[Prompt]:
        """Возвращает список всех промптов"""
        return self.storage.list_prompts()

    def get_prompt(self, prompt_id: str) -> Optional[Prompt]:
        """Интерфейсный метод для получения промпта"""
        return self.storage.load_prompt(prompt_id)  # Используйте метод хранилища

    def search_prompts(self, query: str) -> list[Prompt]:
        """Поиск промптов по запросу"""
        results = []
        for prompt in self.list_prompts():
            if query in prompt.title.lower() or query in prompt.description.lower():
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

        updated_data = self.prompts[prompt_id].dict()
        updated_data.update(new_data)
        updated_prompt = Prompt(**updated_data)

        self.prompts[prompt_id] = updated_prompt
        self.storage.save_prompt(updated_prompt)

    def delete_prompt(self, prompt_id: str):
        self.logger.warning(f"Удаление промпта {prompt_id}")
        # Используйте self.storage.path вместо base_path
        file_path = self.storage.storage_path / f"{prompt_id}.json"
        if file_path.exists():
            file_path.unlink()

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

    def search_prompts(self, query: str, category: str = None):
        """Поиск промптов по запросу и категории"""
        results = []
        for prompt in self.prompts.values():
            if (query.lower() in prompt.title.lower() or
                    query.lower() in prompt.description.lower() or
                    query.lower() in prompt.content.lower()):
                if not category or prompt.category == category:
                    results.append(prompt)
        return results

