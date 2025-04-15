import json
import logging
import string
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from PyQt6.QtCore import QSettings

from src.category_manager import CategoryManager
from src.models import Prompt
from src.storage import LocalStorage


class PromptManager:
    prompts: dict[string, Prompt]

    def __init__(self, storage_path=None):
        self.logger = logging.getLogger(__name__)
        # Загрузка настроек
        settings = QSettings("YourCompany", "YourApp")
        if storage_path is None:
            storage_path = settings.value("prompts_path", "prompts")

        self.logger.debug(f"Инициализация PromptManager с путем: {storage_path}")
        
        self.cat_manager = CategoryManager()
        self.storage = LocalStorage(storage_path)
        self.prompts = {}  # Инициализируем пустым словарем
        self.storage_path = Path(storage_path)
        
        try:
            self.load_all_prompts()
        except Exception as e:
            self.logger.error(f"Ошибка при начальной загрузке промптов: {str(e)}", exc_info=True)

    def load_all_prompts(self):
        """Загрузка всех промптов в кэш при старте"""
        self.logger.debug("Начало загрузки всех промптов")
        try:
            prompts = self.storage.list_prompts()
            self.logger.debug(f"Получено промптов от storage: {len(prompts)}")
            
            for prompt in prompts:
                self.prompts[prompt.id] = prompt
                
            self.logger.info(f"Загружено {len(self.prompts)} промптов")
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке промптов: {str(e)}", exc_info=True)

    def list_prompts(self) -> list[Prompt]:
        """Возвращает список всех промптов"""
        self.logger.debug(f"Запрошен список промптов, в кэше: {len(self.prompts)}")
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
            # Извлекаем текст из контента с учетом возможных типов
            if isinstance(prompt.content, dict):
                content_text = " ".join(str(v) for v in prompt.content.values())
            else:
                content_text = str(prompt.content)

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
        prompt_data = {
            'id': prompt_data.get('id', str(uuid4())),
            'created_at': prompt_data.get('created_at', datetime.utcnow()),
            'updated_at': prompt_data.get('updated_at', datetime.utcnow()),
            **prompt_data  # Остальные данные промпта
        }
        # Создаем и валидируем промпт
        prompt = Prompt(**prompt_data)

        # Проверяем уникальность ID
        self.validate_unique(prompt.id)

        # Сохраняем промпт
        self.prompts[prompt.id] = prompt
        self.storage.save_prompt(prompt)

    def edit_prompt(self, prompt_id: str, new_data: dict):
        self.logger.debug(f"Редактирование промпта {prompt_id} с данными: {new_data}")
        current_prompt = self.prompts.get(prompt_id)
        if not current_prompt:
            raise ValueError("Промпт не найден")

        # Проверяем изменение категории
        old_category = current_prompt.category
        new_category = new_data.get('category', old_category)

        # Обновляем данные промпта
        updated_data = current_prompt.model_dump()
        updated_data.update(new_data)
        updated_prompt = Prompt(**updated_data)

        # Если категория изменилась — перемещаем файл
        if new_category != old_category:
            try:
                self.storage.move_prompt_file(prompt_id, old_category, new_category)
            except FileNotFoundError as e:
                # Если файл не найден в категории, ищем в корне и перемещаем
                if old_category == "general":
                    self.storage.move_prompt_file(prompt_id, "",
                                                  new_category)  # Пустая категория = корень
                else:
                    raise e

        # Обновляем категорию в объекте промпта
        updated_prompt.category = new_category  # Важно!

        # Обновляем кэш и сохраняем
        self.prompts[prompt_id] = updated_prompt
        self.storage.save_prompt(updated_prompt)  # Теперь сохраняет в новую категорию

    def delete_prompt(self, prompt_id: str):
        self.logger.warning(f"Удаление промпта {prompt_id}")
        prompt = self.prompts[prompt_id]
        self.storage.delete_prompt(prompt_id, prompt.category)  # Делегируем удаление файлу Storage
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
