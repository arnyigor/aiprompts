import json
import logging
from collections.abc import Iterable
from typing import Any, Dict, List, Optional, Union, Tuple

import requests

from interfaces import (
    ProviderClient,
    LLMConnectionError, LLMRequestError, LLMResponseError, LLMTimeoutError
)

log = logging.getLogger(__name__)


class OllamaClient(ProviderClient):
    """
    Чистая реализация ProviderClient для нативного API Ollama,
    использующая эндпоинт /api/chat.
    """

    def __init__(self):
        self.endpoint = "http://localhost:11434/api/chat"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        log.info("Нативный Ollama HTTP клиент инициализирован. Endpoint: %s", self.endpoint)

    def prepare_payload(self, messages: List[Dict[str, str]], model: str, *, stream: bool = False, **kwargs: Any) -> \
            Dict[str, Any]:
        top_level_args = {'format', 'keep_alive', 'think'}
        payload = {"model": model, "messages": messages, "stream": stream}
        options = {}
        for key, value in kwargs.items():
            if value is None: continue
            if key in top_level_args:
                payload[key] = value
            else:
                options[key] = value
        if options:
            payload['options'] = options
        return {k: v for k, v in payload.items() if v is not None}

    def send_request(self, payload: Dict[str, Any], api_key: Optional[str] = None) -> Union[
        Dict[str, Any], Iterable[Dict[str, Any]]]:
        """
        Отправляет запрос к API, генерируя информативные и типизированные исключения.
        """
        is_stream = payload.get("stream", False)
        # Таймаут не является частью API Ollama, поэтому его нужно удалить из payload
        timeout = payload.pop('timeout', 180)

        log.info("Отправка запроса на %s (stream=%s)...", self.endpoint, is_stream)
        # log.debug("Payload: %s", json.dumps(payload, indent=2, ensure_ascii=False))

        try:
            resp = self.session.post(self.endpoint, json=payload, stream=is_stream, timeout=timeout)

            # Проверяем на ошибки HTTP (4xx, 5xx)
            if not resp.ok:
                # Пытаемся извлечь детальное сообщение из тела ответа
                try:
                    error_details = resp.json()
                    # Ollama обычно возвращает ошибку в ключе 'error'
                    error_message = error_details.get('error', str(error_details))
                except json.JSONDecodeError:
                    error_message = resp.text.strip()  # Если ответ не JSON

                # Создаем наше кастомное, информативное исключение
                raise LLMRequestError(
                    message=f"Ошибка API: {error_message}",
                    status_code=resp.status_code,
                    response_text=resp.text
                )

            log.info("Запрос к Ollama успешно выполнен.")

            # Обработка успешного ответа
            if is_stream:
                def stream_generator():
                    try:
                        for line in resp.iter_lines():
                            if line:
                                yield json.loads(line)
                    except requests.exceptions.ChunkedEncodingError as e:
                        raise LLMResponseError(f"Ошибка при чтении потокового ответа: {e}") from e
                    except json.JSONDecodeError as e:
                        raise LLMResponseError(f"Ошибка декодирования JSON из потока: {e}") from e

                return stream_generator()
            else:
                try:
                    return resp.json()
                except json.JSONDecodeError as e:
                    raise LLMResponseError(f"Ошибка декодирования JSON из ответа: {e}") from e

        # --- Обработка специфичных ошибок requests ---
        except requests.exceptions.Timeout as e:
            raise LLMTimeoutError(f"Таймаут запроса к {self.endpoint} (>{timeout}s)") from e
        except requests.exceptions.ConnectionError as e:
            raise LLMConnectionError(f"Ошибка соединения с {self.endpoint}. Сервер недоступен.") from e
        except requests.exceptions.RequestException as e:
            # Общая ошибка для всех остальных проблем requests
            raise LLMConnectionError(f"Сетевая ошибка Ollama: {e}") from e

    def extract_choices(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [response] if 'message' in response else []

    def extract_content_from_choice(self, choice: Dict[str, Any]) -> str:
        return choice.get("message", {}).get("content", "")

    def extract_delta_from_chunk(self, chunk: Dict[str, Any]) -> Tuple[str, Optional[Dict], Optional[str]]:
        """
        Извлекает данные из чанка ответа Ollama, включая "мышление" модели.

        В потоковом режиме Ollama присылает чанки, где "мышление" и "контент"
        находятся внутри ключа 'message'. Этот метод обрабатывает оба поля.

        Args:
            chunk: Один чанк (словарь) из итератора ответа Ollama.

        Returns:
            Кортеж (content, logprobs, finish_reason), где:
            - content (str): Фрагмент сгенерированного текста или "мышления".
            - logprobs (Optional[Dict]): Всегда None для Ollama.
            - finish_reason (Optional[str]): Причина завершения или None.
        """
        thinking_part = ""
        content_part = ""

        # Структура чанка Ollama: { "message": { "content": "...", "thinking": "..." } }
        message = chunk.get("message", {})
        if isinstance(message, dict):
            # Извлекаем "мышление", если оно есть
            thinking_text = message.get("thinking")
            if thinking_text:
                thinking_part = f"<think>{thinking_text}</think>"

            # Извлекаем обычный контент
            content_part = message.get("content", "")

        # Приоритет отдаем "мышлению", если оно есть в данном чанке
        final_content = thinking_part if thinking_part else content_part

        # Извлекаем причину завершения из корня чанка
        finish_reason = chunk.get("done_reason")

        # Ollama API в текущей версии не предоставляет logprobs в стандартном виде
        logprobs = None

        return final_content, logprobs, finish_reason

    def extract_metadata_from_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлекает метаданные из финального ответа или чанка.
        Поддерживает различные форматы провайдеров.
        """
        try:
            metadata = {}

            # OpenAI-style usage
            usage_stats = response.get("usage", {})
            if usage_stats:
                metadata.update({
                    "prompt_eval_count": usage_stats.get("prompt_tokens"),
                    "eval_count": usage_stats.get("completion_tokens"),
                    "total_tokens": usage_stats.get("total_tokens"),
                })

            # Ollama-style метаданные
            ollama_fields = [
                "total_duration", "load_duration", "prompt_eval_count",
                "prompt_eval_duration", "eval_count", "eval_duration"
            ]
            for field in ollama_fields:
                if field in response:
                    metadata[field] = response[field]

            # Дополнительные поля
            additional_fields = ["model", "created", "id", "object", "system_fingerprint"]
            for field in additional_fields:
                if field in response:
                    metadata[field] = response[field]

            # Убираем None значения
            return {k: v for k, v in metadata.items() if v is not None}

        except Exception as e:
            log.warning(f"Ошибка при извлечении метаданных из ответа: {e}")
            return {}

    def extract_metadata_from_chunk(self, chunk: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Извлекает метаданные из чанка. Возвращает словарь с метаданными если чанк финальный,
        иначе возвращает None.
        """
        try:
            # Проверяем, является ли чанк финальным (содержит метаданные)
            if chunk.get("done", False) is True:
                return self.extract_metadata_from_response(chunk)

            # Также проверяем другие возможные индикаторы финального чанка
            if chunk.get("choices", [{}])[0].get("finish_reason") is not None:
                return self.extract_metadata_from_response(chunk)

            # Для Ollama - проверяем наличие метаданных
            ollama_metadata_fields = [
                "total_duration", "load_duration", "prompt_eval_count",
                "prompt_eval_duration", "eval_count", "eval_duration"
            ]
            if any(field in chunk for field in ollama_metadata_fields):
                return self.extract_metadata_from_response(chunk)

            return None

        except Exception as e:
            log.warning(f"Ошибка при проверке метаданных в чанке: {e}")
            return None
