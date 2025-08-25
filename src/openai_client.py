import json
import time
from collections.abc import Iterable, Generator
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union, Tuple
import requests
import logging

from .interfaces import ProviderClient, LLMResponseError, LLMConnectionError

log = logging.getLogger(__name__)

class OpenAICompatibleClient(ProviderClient):
    """
    Клиент для взаимодействия с любым API, совместимым с OpenAI.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.openai.com/v1"):
        self.base_url = base_url.rstrip('/').strip()
        # Сохраняем базовый URL, endpoint будем формировать динамически
        log.info("OpenAICompatibleClient инициализирован. Base URL: %s", self.base_url)

        self.session = requests.Session()
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self.session.headers.update(headers)

    def prepare_payload(self, messages: List[Dict[str, str]], model: str, *, stream: bool = False, **kwargs: Any) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"model": model, "messages": messages, "stream": stream}

        # Проверяем, используем ли мы Hugging Face Inference Providers
        is_hf_router = getattr(self, 'base_url', '').startswith('https://router.huggingface.co')

        if is_hf_router:
            # Для Hugging Face устанавливаем provider по умолчанию, если не задан
            if 'provider' not in kwargs and 'provider' not in payload:
                payload["provider"] = "auto"

        payload.update(kwargs)
        return {k: v for k, v in payload.items() if v is not None}

    def send_request(self, payload: Dict[str, Any], api_key: Optional[str] = None) -> Union[Dict[str, Any], Iterable[Dict[str, Any]]]:
        is_stream = payload.get("stream", False)
        timeout = payload.pop('timeout', 180)

        # Подготавливаем заголовки
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Формируем endpoint: используем базовый URL + /chat/completions
        url = f"{self.base_url}/chat/completions"
        request_payload = payload # Используем стандартный OpenAI формат для всех

        log.info("Отправка запроса на %s (stream=%s)...", url, is_stream)
        try:
            resp = self.session.post(url, json=request_payload, headers=headers, stream=is_stream, timeout=timeout)
            resp.raise_for_status()
            log.info("Запрос успешно выполнен.")
            if is_stream:
                return self._handle_stream(resp)
            else:
                return resp.json()
        except requests.exceptions.RequestException as e:
            log.error("Сетевая ошибка при запросе к %s: %s", url, e)
            raise LLMConnectionError(f"Сетевая ошибка: {e}") from e

    def _handle_stream(self, response: requests.Response) -> Generator[Dict[str, Any], None, None]:
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    content = decoded_line[6:]
                    if content.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(content)
                        yield chunk
                        if chunk.get("choices", [{}])[0].get("finish_reason") is not None:
                            break
                    except json.JSONDecodeError:
                        log.warning("Не удалось декодировать JSON-чанк: %s", content)

    def extract_choices(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        return response.get("choices", [])

    def extract_content_from_choice(self, choice: Dict[str, Any]) -> str:
        return choice.get("message", {}).get("content", "")

    def extract_delta_from_chunk(self, chunk: Dict[str, Any]) -> Tuple[str, Optional[Dict], Optional[str]]:
        """
        Извлекает из чанка ответа текст, информацию о вероятностях токенов (logprobs)
        и причину завершения генерации.

        Args:
            chunk (Dict[str, Any]): Чанк данных, полученный от API.

        Returns:
            Tuple[str, Optional[Dict], Optional[str]]: Кортеж, содержащий:
            - Текстовое содержимое дельты (content)
            - Информацию о logprobs, если она доступна
            - Причину завершения генерации, если она указана
        """
        choices = chunk.get("choices", [])
        if not choices:
            return "", None, None

        choice = choices[0]
        delta = choice.get("delta", {})
        content = delta.get("content", "")

        # Извлечение logprobs, если они есть в чанке
        logprobs = choice.get("logprobs")

        # Извлечение причины завершения
        finish_reason = choice.get("finish_reason")

        return content, logprobs, finish_reason

    def extract_metadata_from_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлекает метаданные, предоставленные сервером в API-ответе.
        Реализует логику "Приоритет и Фолбэк" и поддерживает расширенный набор полей.
        """
        try:
            metadata = {}

            # --- ШАГ 1: Прямое извлечение (Приоритетный источник) ---
            # Расширяем список полей, которые могут лежать на верхнем уровне ответа.
            direct_fields = [
                # Стандартные/Общие поля
                "model", "created", "id", "object", "system_fingerprint",

                # Ollama-специфичные поля
                "total_duration", "load_duration", "prompt_eval_count",
                "prompt_eval_duration", "eval_count", "eval_duration",

                # НОВЫЕ ПОЛЯ, обнаруженные в логах от "Chutes"
                "provider",
                "native_finish_reason" # Может быть внутри 'choices', но проверим и здесь
            ]
            for field in direct_fields:
                if field in response:
                    metadata[field] = response[field]

            # Также проверим 'native_finish_reason' внутри 'choices', где он чаще всего бывает
            if 'native_finish_reason' not in metadata:
                choices = response.get("choices")
                if choices and isinstance(choices, list) and len(choices) > 0:
                    if 'native_finish_reason' in choices[0]:
                        metadata['native_finish_reason'] = choices[0]['native_finish_reason']

            # --- ШАГ 2: Логика фолбэка для количества токенов (OpenAI-style) ---
            usage_stats = response.get("usage") or {}
            if 'prompt_eval_count' not in metadata and 'prompt_tokens' in usage_stats:
                metadata['prompt_eval_count'] = usage_stats['prompt_tokens']
            if 'eval_count' not in metadata and 'completion_tokens' in usage_stats:
                metadata['eval_count'] = usage_stats['completion_tokens']

            # --- ШАГ 3: Финальная очистка ---
            return {k: v for k, v in metadata.items() if v is not None}

        except Exception as e:
            log.warning(f"Ошибка при извлечении метаданных из ответа: {e}")
            return {}

    def extract_metadata_from_chunk(self, chunk: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Проверяет, является ли чанк финальным, и если да, извлекает из него метаданные.
        Возвращает словарь с метаданными для финального чанка или None для промежуточных.
        """

        # Признак №1: OpenAI-style (наличие finish_reason)
        is_final = False
        choices = chunk.get("choices")
        if choices and isinstance(choices, list) and len(choices) > 0:
            if choices[0].get("finish_reason") is not None:
                is_final = True

        # --- ШАГ 2: Если чанк финальный, делегируем извлечение ---
        if is_final:
            # Мы не гадаем, что внутри чанка. Мы просто передаем его дальше.
            # Наша универсальная функция extract_metadata_from_response сама разберется,
            # есть ли там 'usage', поля Ollama или что-то еще.
            return self.extract_metadata_from_response(chunk)

        # --- ШАГ 3: Если это обычный чанк с контентом, возвращаем None ---
        return None