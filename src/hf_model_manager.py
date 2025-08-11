import json
import logging
import os
from typing import Dict, Any, List, Optional

from llm_settings import Settings


class HFModelManager:
    """Менеджер для работы с конфигурациями моделей Hugging Face"""

    def __init__(self, settings: Settings):
        """
        Инициализация менеджера моделей.
        
        Args:
            settings: Объект настроек приложения
        """
        self.logger = logging.getLogger(__name__)
        self.settings = settings
        self.config_path = self.settings.get_config_path("huggingface_models.json")
        self.models = self._load_models()

    def _load_models(self) -> dict:
        """Загружает список моделей из файла конфигурации"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    models = json.load(f)
            else:
                models = {}
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке конфигураций: {str(e)}")
            models = {}

        if not models:
            # Добавляем модели по умолчанию
            models = {
                "Qwen2.5-7B-Instruct": {
                    "id": "Qwen/Qwen2.5-7B-Instruct",
                    "description": "Флагманская модель от Alibaba. Отличное следование инструкциям, поддержка множества языков (включая русский) и большой контекст. Идеальный баланс мощности и скорости.",
                    "parameters": {
                        "max_new_tokens": 4096,  # Модель поддерживает до 128k, но 4096 - хороший старт
                        "temperature": 0.7,
                        "top_p": 0.95,
                        "repetition_penalty": 1.15 # Qwen модели хорошо реагируют на чуть более высокий penalty
                    }
                },
                "Qwen2.5-3B-Instruct": {
                    "id": "Qwen/Qwen2.5-3B-Instruct",
                    "description": "Более быстрая и компактная версия 7B. Отлично подходит для задач, где важна скорость ответа или для пакетной обработки. Высокая надежность запуска через API.",
                    "parameters": {
                        "max_new_tokens": 4096,
                        "temperature": 0.7,
                        "top_p": 0.95,
                        "repetition_penalty": 1.15
                    }
                },
                "Mistral-7B-Instruct": {
                    "id": "mistralai/Mistral-7B-Instruct-v0.2",
                    "description": "Мощная модель с хорошим балансом качества и производительности. Отлично подходит для русского языка.",
                    "parameters": {
                        "max_new_tokens": 4096,
                        "temperature": 0.7,
                        "top_p": 0.95,
                        "repetition_penalty": 1.1
                    }
                },
                "Zephyr-7B": {
                    "id": "HuggingFaceH4/zephyr-7b-beta",
                    "description": "Специализированная модель для инструкций и промптов. Хорошо следует указаниям.",
                    "parameters": {
                        "max_new_tokens": 4096,
                        "temperature": 0.7,
                        "top_p": 0.95,
                        "repetition_penalty": 1.1
                    }
                },
                "SOLAR-10.7B-Instruct": {
                    "id": "upstage/SOLAR-10.7B-Instruct-v1.0",
                    "description": "Продвинутая модель с отличным пониманием контекста и генерацией текста.",
                    "parameters": {
                        "max_new_tokens": 4096,
                        "temperature": 0.7,
                        "top_p": 0.95,
                        "repetition_penalty": 1.2
                    }
                },
                "Phi-2": {
                    "id": "microsoft/phi-2",
                    "description": "Компактная но мощная модель от Microsoft. Хорошо работает с техническими текстами.",
                    "parameters": {
                        "max_new_tokens": 2048,
                        "temperature": 0.7,
                        "top_p": 0.95,
                        "repetition_penalty": 1.1
                    }
                }
            }
            self._save_models(models)
        return models

    def _save_models(self, models: dict):
        """Сохраняет список моделей в файл конфигурации"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(models, f, ensure_ascii=False, indent=4)
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении конфигураций: {str(e)}")

    def get_model_names(self) -> list:
        """Возвращает список имен моделей"""
        return list(self.models.keys())

    def get_model_path(self, model_name: str) -> str:
        """Возвращает путь к модели по ее имени"""
        models = self.models
        self.logger.info(f"Выбранная модель {model_name} список моделей {models}")
        if model_name not in models:
            raise ValueError(f"Модель {model_name} не найдена")
        return self.models[model_name]["id"]

    def get_model_parameters(self, model_name: str) -> dict:
        """Возвращает параметры модели по ее имени"""
        if model_name not in self.models:
            raise ValueError(f"Модель {model_name} не найдена")
        return self.models[model_name].get("parameters", {})

    def get_model_description(self, model_name: str) -> str:
        """Возвращает описание модели по ее имени"""
        if model_name not in self.models:
            raise ValueError(f"Модель {model_name} не найдена")
        return self.models[model_name].get("description", "")

    def add_model(self, name: str, model_id: str, description: str, parameters: dict = None):
        """Добавляет новую модель"""
        if name in self.models:
            raise ValueError(f"Модель с именем {name} уже существует")

        if not model_id or "/" not in model_id:
            raise ValueError("Некорректный путь к модели")

        self.models[name] = {
            "id": model_id,
            "description": description,
            "parameters": parameters or {
                "max_new_tokens": 4096,
                "temperature": 0.7,
                "top_p": 0.95,
                "repetition_penalty": 1.1
            }
        }
        self._save_models(self.models)

    def update_model(self, name: str, model_id: str, description: str, parameters: dict = None):
        """Обновляет существующую модель"""
        if name not in self.models:
            raise ValueError(f"Модель {name} не найдена")

        if not model_id or "/" not in model_id:
            raise ValueError("Некорректный путь к модели")

        self.models[name].update({
            "id": model_id,
            "description": description,
            "parameters": parameters or self.models[name].get("parameters", {})
        })
        self._save_models(self.models)

    def delete_model(self, name: str):
        """Удаляет модель"""
        if name not in self.models:
            raise ValueError(f"Модель {name} не найдена")
        del self.models[name]
        self._save_models(self.models)

    def validate_model_path(self, model_id: str) -> bool:
        """Проверяет корректность пути к модели"""
        if not model_id or "/" not in model_id:
            return False
        try:
            from huggingface_hub import HfApi
            api = HfApi(token=self.settings.get_api_key("huggingface"))
            # Проверяем существование модели через API
            api.model_info(model_id)
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при проверке модели {model_id}: {str(e)}")
            return False

    def get_model_params(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Получает параметры модели по её ID"""
        for model in self.models.values():
            if model["id"] == model_id:
                return model["parameters"]
        return None

    def get_model_list(self) -> List[str]:
        """Возвращает список ID всех доступных моделей"""
        return [model["id"] for model in self.models.values()]

    def get_model_config(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Получает полную конфигурацию модели по её имени"""
        return self.models.get(model_name)

    def validate_model_config(self, config: Dict[str, Any]) -> bool:
        """Проверяет корректность конфигурации модели"""
        required_fields = ["id", "parameters", "description"]
        required_params = ["max_new_tokens", "temperature", "top_p", "repetition_penalty"]

        # Проверяем наличие всех обязательных полей
        if not all(field in config for field in required_fields):
            return False

        # Проверяем наличие всех обязательных параметров
        if not all(param in config["parameters"] for param in required_params):
            return False

        # Проверяем типы данных и диапазоны значений
        params = config["parameters"]
        if not isinstance(params["max_new_tokens"], int) or params["max_new_tokens"] <= 0:
            return False
        if not isinstance(params["temperature"], (int, float)) or not 0 <= params[
            "temperature"] <= 1:
            return False
        if not isinstance(params["top_p"], (int, float)) or not 0 <= params["top_p"] <= 1:
            return False
        if not isinstance(params["repetition_penalty"], (int, float)) or params[
            "repetition_penalty"] < 1:
            return False

        return True
