import logging
import os

from huggingface_hub import InferenceClient


class HuggingFaceInference:
    def __init__(self):
        print("Инициализация HuggingFaceInference...")
        self.api_key = os.getenv("HUGGINGFACE_API_KEY")
        if not self.api_key:
            raise ValueError("API-ключ Hugging Face не найден в переменных окружения")

        self.logger = logging.getLogger(__name__)
        self.client = InferenceClient(token=self.api_key)
        self.model_name = "mistralai/Mistral-7B-Instruct-v0.2"

        self.logger.info(f"Инициализация HuggingFaceInference завершена")

    def query_model(self, messages: list[dict], **kwargs) -> str:
        try:
            prompt = self._format_messages(messages)

            self.logger.info(f"Отправка запроса к модели {self.model_name}")
            self.logger.debug(f"Промпт: {prompt[:100]}...")
            self.logger.debug(f"Параметры запроса: {kwargs}")

            try:
                response = self.client.text_generation(
                    prompt=prompt,
                    model=self.model_name,
                    **kwargs
                )

                self.logger.debug(f"Получен ответ типа: {type(response)}")
                self.logger.debug(f"Ответ: {response}")

                if isinstance(response, str):
                    return response
                elif hasattr(response, 'generated_text'):
                    return response.generated_text
                else:
                    return str(response)

            except Exception as e:
                raise Exception(f"Ошибка при выполнении запроса: {str(e)}")

        except Exception as e:
            error_msg = f"Ошибка при запросе к модели: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)

    def _format_messages(self, messages: list[dict]) -> str:
        """Форматирует сообщения в промпт для модели"""
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