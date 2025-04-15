import logging
from typing import Optional, Generator

from huggingface_hub import InferenceClient

from .hf_model_manager import HFModelManager
from .llm_settings import Settings


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
        """
        Отправляет запрос к модели и возвращает генератор для потокового ответа.
        
        Args:
            model_name: Имя модели из списка доступных моделей
            messages: Список сообщений в формате [{"role": "user", "content": "текст"}, ...]
            **kwargs: Дополнительные параметры для генерации
            
        Returns:
            Generator[str, None, None]: Генератор для потокового ответа
            
        Raises:
            ValueError: Если модель не найдена или возникла ошибка при запросе
        """
        try:
            # Получаем путь к модели и параметры
            model_path = self.model_manager.get_model_path(model_name)
            model_params = self.model_manager.get_model_parameters(model_name)

            # Объединяем параметры по умолчанию с переданными
            params = model_params.copy()
            params.update(kwargs)
            
            # Включаем потоковый режим и убеждаемся, что параметры корректны
            params['stream'] = True
            params['max_new_tokens'] = int(params.get('max_new_tokens', 2048))
            params['temperature'] = float(params.get('temperature', 0.7))
            params['top_p'] = float(params.get('top_p', 0.95))

            prompt = self._format_messages(messages)

            self.logger.info(f"Отправка запроса к модели {model_path}")
            self.logger.debug(f"Промпт: {prompt}")
            self.logger.debug(f"Параметры запроса: {params}")

            try:
                # Получаем итератор для потокового ответа
                response_iterator = self.client.text_generation(
                    prompt=prompt,
                    model=model_path,
                    **params
                )
                
                self.logger.debug("Начало получения потокового ответа")
                
                for response in response_iterator:
                    self.logger.debug(f"Получен токен: {response}")
                    
                    if isinstance(response, str):
                        self.logger.debug(f"Обработка строкового токена: {response}")
                        yield response
                    elif hasattr(response, 'token'):
                        text = response.token.text
                        self.logger.debug(f"Обработка токена объекта: {text}")
                        yield text
                    elif hasattr(response, 'generated_text'):
                        text = response.generated_text
                        self.logger.debug(f"Обработка полного текста: {text}")
                        yield text
                    else:
                        text = str(response)
                        self.logger.debug(f"Обработка неизвестного формата: {text}")
                        yield text

                self.logger.debug("Завершение потокового ответа")

            except Exception as e:
                error_msg = f"Ошибка при выполнении запроса: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                raise Exception(error_msg)

        except Exception as e:
            error_msg = f"Ошибка при запросе к модели: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)

    def _format_messages(self, messages: list[dict]) -> str:
        """
        Форматирует сообщения в промпт для модели.
        
        Args:
            messages: Список сообщений в формате [{"role": "user", "content": "текст"}, ...]
            
        Returns:
            str: Отформатированный промпт
        """
        formatted_messages = []
        for message in messages:
            role = message.get("role", "").capitalize()
            content = message.get("content", "")
            # Добавляем специальные токены для лучшего форматирования
            formatted_messages.append(f"<|{role}|>: {content}")
        # Добавляем токен для ответа ассистента
        formatted_text = "\n".join(formatted_messages)
        formatted_text += "\n<|Assistant|>: "
        return formatted_text

    def _clean_response(self, response: str) -> str:
        """Очищает ответ модели от специальных токенов"""
        # Убираем специальные токены
        tokens_to_remove = [
            "<|System|>:", "<|Assistant|>:", "<|User|>:",
            "<s>", "</s>", "[INST]", "[/INST]"
        ]

        cleaned = response
        for token in tokens_to_remove:
            cleaned = cleaned.replace(token, "")

        # Убираем лишние пробелы и переносы строк
        cleaned = cleaned.strip()

        return cleaned

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
