import logging
import os

from huggingface_hub import InferenceClient
from requests.exceptions import HTTPError


class HuggingFaceInference:
    def __init__(self):
        print("Инициализация HuggingFaceInference...")
        api_key = os.getenv("HUGGINGFACE_API_KEY")
        if not api_key:
            raise ValueError("API-ключ Hugging Face не найден в переменных окружения")
        model_name: str = "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
        self.logger = logging.getLogger(__name__)
        self.client = InferenceClient(
            model=model_name,
            provider="novita",
            api_key=api_key
        )
        self.model_name = model_name

    def query_model(self, messages: list[dict], stream: bool = True) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.5,
                max_tokens=2048,
                top_p=0.7,
                stream=stream
            )
            response_text = ""
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    response_text += chunk.choices[0].delta.content
            return response_text
        except HTTPError as e:  # Теперь ловим HTTPError
            self.logger.error(f"Ошибка Hugging Face API: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Неизвестная ошибка: {str(e)}")
            raise
