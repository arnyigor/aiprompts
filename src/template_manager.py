# template_manager.py
from typing import Dict, List

from src.models import Prompt


class TemplateManager:
    def __init__(self):
        self.templates: Dict[str, Prompt] = {}

    def register_template(self, template_id: str, template: Prompt):
        """Регистрирует новый шаблон"""
        if template_id in self.templates:
            raise ValueError(f"Шаблон {template_id} уже существует")
        self.templates[template_id] = template

    def apply_template(self, template_id: str, **kwargs) -> Prompt:
        """Применяет шаблон с заданными параметрами"""
        if template_id not in self.templates:
            raise ValueError(f"Шаблон {template_id} не найден")

        base_template = self.templates[template_id]
        new_prompt_data = base_template.dict()

        # Обновляем поля из kwargs
        new_prompt_data.update(kwargs)
        new_prompt_data['id'] = kwargs.get('id', f"{template_id}-{self._generate_suffix()}")
        new_prompt_data['template'] = template_id  # Связь с шаблоном

        return Prompt(**new_prompt_data)

    def _generate_suffix(self) -> str:
        """Генерирует уникальный суффикс для ID"""
        import uuid
        return str(uuid.uuid4())[:8]

    def list_templates(self) -> List[str]:
        """Возвращает список доступных шаблонов"""
        return list(self.templates.keys())
