import json
import logging
from typing import List, Dict, Generator, Union

import requests


class LMStudioInference:
    """Класс для работы с LMStudio API"""

    CHAT_FORMATS = {
        "chatml": {
            "system": "<|im_start|>system\n{message}<|im_end|>\n",
            "user": "<|im_start|>user\n{message}<|im_end|>\n",
            "assistant": "<|im_start|>assistant\n{message}<|im_end|>\n"
        },
        "alpaca": {
            "system": "### System:\n{message}\n\n",
            "user": "### User:\n{message}\n\n",
            "assistant": "### Assistant:\n{message}\n\n"
        },
        "vicuna": {
            "system": "SYSTEM: {message}\n",
            "user": "USER: {message}\n",
            "assistant": "ASSISTANT: {message}\n"
        },
        "openai": {
            "system": "System: {message}\n",
            "user": "User: {message}\n",
            "assistant": "Assistant: {message}\n"
        },
        "llama2": {
            "system": "[INST] <<SYS>>\n{message}\n<</SYS>>\n\n",
            "user": "{message} [/INST]\n",
            "assistant": "{message}\n"
        },
        "mistral": {
            "system": "<s>[INST] {message} [/INST]",
            "user": "[INST] {message} [/INST]",
            "assistant": "{message}</s>"
        }
    }

    def __init__(self, base_url: str = "http://localhost:1234/v1"):
        self.logger = logging.getLogger(__name__)
        self.base_url = base_url
        # self.logger.info("Инициализация LMStudioInference...")

    def format_messages(self, messages: List[Dict[str, str]], chat_format: str = "chatml") -> str:
        """
        Форматирует сообщения в соответствии с выбранным форматом чата
        
        Args:
            messages: Список сообщений
            chat_format: Формат чата (chatml, alpaca, vicuna, openai, llama2, mistral)
            
        Returns:
            str: Отформатированный текст
        """
        chat_format = chat_format.lower()
        if chat_format not in self.CHAT_FORMATS:
            self.logger.warning(f"Неизвестный формат чата: {chat_format}, используется ChatML")
            chat_format = "chatml"

        format_templates = self.CHAT_FORMATS[chat_format]
        formatted_messages = []

        for message in messages:
            role = message["role"]
            content = message["content"]

            if role in format_templates:
                formatted_message = format_templates[role].format(message=content)
                formatted_messages.append(formatted_message)
            else:
                self.logger.warning(f"Неизвестная роль: {role}, пропускается")

        return "".join(formatted_messages)

    def _stream_response(self, response: requests.Response) -> Generator[str, None, None]:
        """
        Обрабатывает потоковый ответ от API
        
        Args:
            response: Ответ от API
            
        Yields:
            str: Части ответа
        """
        try:
            self.logger.info("Начало получения потокового ответа")
            chunks_received = 0
            
            for line in response.iter_lines():
                if line:
                    try:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data = line[6:]  # Убираем префикс 'data: '
                            if data == '[DONE]':
                                self.logger.info(f"Получение завершено. Всего получено чанков: {chunks_received}")
                                break
                                
                            try:
                                json_data = json.loads(data)
                                if "choices" in json_data and len(json_data["choices"]) > 0:
                                    delta = json_data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        content = delta["content"]
                                        chunks_received += 1
                                        if chunks_received % 50 == 0:  # Логируем каждые 50 чанков
                                            self.logger.info(f"Получено чанков: {chunks_received}")
                                        yield content
                            except json.JSONDecodeError as je:
                                self.logger.warning(f"Ошибка декодирования JSON: {str(je)}")
                                continue
                    except UnicodeDecodeError as ue:
                        self.logger.warning(f"Ошибка декодирования строки: {str(ue)}")
                        continue
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке потокового ответа: {str(e)}", exc_info=True)
            raise

    def query_model(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        """
        Отправляет запрос к модели и возвращает генератор для потокового ответа
        
        Args:
            messages: Список сообщений
            **kwargs: Дополнительные параметры
            
        Returns:
            Generator[str, None, None]: Генератор для потокового ответа
            
        Raises:
            ConnectionError: Если не удалось подключиться к API
            Exception: При других ошибках
        """
        try:
            # Форматируем сообщения в соответствии с выбранным форматом чата
            chat_format = kwargs.pop("chat_format", "chatml")
            formatted_prompt = self.format_messages(messages, chat_format)

            # Формируем URL для запроса
            url = f"{self.base_url}/chat/completions"

            # Подготавливаем параметры
            params = {
                "model": kwargs.get("model", "local-model"),
                "messages": [{"role": "user", "content": formatted_prompt}],
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_new_tokens", 4096),
                "top_p": kwargs.get("top_p", 0.95),
                "repeat_penalty": kwargs.get("repeat_penalty", 1.1),
                "presence_penalty": kwargs.get("presence_penalty", 0.0),
                "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
                "stream": True  # Включаем потоковый режим
            }

            self.logger.debug(f"Отправка запроса к LMStudio: {url}")
            self.logger.debug(f"Параметры: {params}")

            # Отправляем запрос
            response = requests.post(url, json=params, stream=True)
            response.raise_for_status()

            # Возвращаем генератор для потокового ответа
            return self._stream_response(response)

        except requests.exceptions.ConnectionError:
            error_msg = "Не удалось подключиться к LMStudio. Убедитесь, что приложение запущено и API доступен."
            self.logger.error(error_msg)
            raise ConnectionError(error_msg)
        except Exception as e:
            error_msg = f"Ошибка при запросе к LMStudio: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)

    def check_connection(self) -> bool:
        """
        Проверяет доступность LMStudio API
        
        Returns:
            bool: True если API доступен, False в противном случае
        """
        try:
            response = requests.get(f"{self.base_url}/models")
            return response.status_code == 200
        except:
            return False
