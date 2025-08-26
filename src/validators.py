from models import Prompt, Variable
from typing import List

def validate_prompt(prompt: Prompt):
    """Полная валидация промпта"""
    # Проверка уникальности ID (логика зависит от хранилища)
    # Здесь предполагается, что проверка уникальности выполняется в PromptManager
    _validate_variables(prompt.variables)
    if not prompt.content.get('ru') and not prompt.content.get('en'):
        raise ValueError("Контент должен содержать русскую или английскую версию")

def _validate_variables(variables: List[Variable]):
    """Проверка корректности переменных"""
    for var in variables:
        if var.type not in ["string", "number", "list"]:
            raise ValueError(f"Неподдерживаемый тип переменной: {var.type}")
        if not var.name.isidentifier():
            raise ValueError(f"Некорректное имя переменной: {var.name}")
        if var.type == "list" and not var.examples:
            raise ValueError(f"Для списковых переменных нужны примеры: {var.name}")
