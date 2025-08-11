import logging
from typing import Generator, Dict, Any

from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError

from hf_model_manager import HFModelManager
from llm_settings import Settings

class HuggingFaceAPI:
    """API для работы с моделями Hugging Face"""

    def __init__(self, settings: Settings):
        """
        Инициализация API.
        
        Args:
            settings: Объект настроек приложения
        """
        self.settings = settings
        self.api_key = self.settings.get_api_key("huggingface")
        self.client = InferenceClient(token=self.api_key) if self.api_key else InferenceClient()
        self.model_manager = HFModelManager(self.settings)
        self.logger = logging.getLogger(__name__)

    def query_model(self, model_name: str, messages: list[dict], **kwargs) -> Generator[str, None, None]:
        try:
            model_path = self.model_manager.get_model_path(model_name)
            model_params = self.model_manager.get_model_parameters(model_name)

            params = model_params.copy()
            params.update(kwargs)

            api_params: Dict[str, Any] = params.copy()
            if 'max_new_tokens' in api_params:
                api_params['max_tokens'] = int(api_params.pop('max_new_tokens'))
            api_params.pop('repetition_penalty', None)
            api_params.pop('stream', None)

            self.logger.info(f"Попытка запроса к модели: {model_path}")

            try:
                # --- ГЛАВНОЕ ИЗМЕНЕНИЕ: ИЗОЛИРОВАННЫЙ КЛИЕНТ И ПРОВЕРКА ---
                # Создаем клиент для конкретной модели, чтобы сразу выявить проблему
                client = InferenceClient(model=model_path, token=self.api_key)

                response_iterator = client.chat_completion(
                    messages=messages,
                    stream=True,
                    **api_params
                )

                for chunk in response_iterator:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content

            # --- УЛУЧШЕННАЯ ОБРАБОТКА ОШИБОК ---
            except StopIteration:
                error_msg = (
                    f"Критическая ошибка: Hugging Face API не может найти доступный сервер (провайдер) для модели '{model_path}'. "
                    "Это не ошибка кода. Попробуйте позже или выберите другую модель."
                )
                self.logger.error(error_msg)
                raise ConnectionError(error_msg) # Используем более подходящий тип исключения

            except HfHubHTTPError as e:
                # Эта ошибка возникает, если модель загружается, но есть другая проблема (например, ошибка 503 Service Unavailable)
                error_msg = f"HTTP ошибка от Hugging Face API для модели '{model_path}': {str(e)}. Сервис может быть перегружен."
                self.logger.error(error_msg, exc_info=True)
                raise ConnectionError(error_msg)

            except Exception as e:
                error_msg = f"Неожиданная ошибка при выполнении запроса к модели '{model_path}': {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                raise Exception(error_msg)

        except Exception as e:
            # Эта ошибка сработает, если проблемы возникли до API запроса (например, в model_manager)
            error_msg = f"Ошибка при подготовке запроса: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)

    def get_available_models(self) -> list:
        """Возвращает список доступных моделей"""
        return self.model_manager.get_model_names()

    def get_model_description(self, model_name: str) -> str:
        """Возвращает описание модели"""
        return self.model_manager.get_model_description(model_name)

    def validate_api_key(self) -> bool:
        """Проверяет валидность API ключа"""
        try:
            # Пробуем получить статус любой публичной модели
            self.client.get_model_status("microsoft/phi-2")
            return True
        except:
            return False
