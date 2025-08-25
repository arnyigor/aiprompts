from collections.abc import Iterable, Generator
from typing import Any, Dict, List, Union
import logging

from src.interfaces import ProviderClient

log = logging.getLogger(__name__)

class LLMClient:
    """
    Универсальный клиент-фасад. Его задача - взять запрос, передать его
    правильному провайдеру и вернуть "сырой" ответ от API.
    """
    def __init__(self, provider: ProviderClient, model_config: Dict[str, Any]):
        self.provider = provider
        self.model_config = model_config
        self.model = model_config.get('name', 'unknown_model')
        log.info("LLMClient создан для модели '%s' с провайдером %s", self.model, provider.__class__.__name__)

    def chat(self, messages: List[Dict[str, str]], *, stream: bool = False, **kwargs: Any) -> Union[Dict[str, Any], Iterable[Dict[str, Any]]]:
        """
        Отправляет запрос к LLM и возвращает "сырой" ответ от провайдера.

        Returns:
            - Если stream=False: Полный JSON-ответ от API в виде словаря.
            - Если stream=True: Итератор по JSON-чанкам ответа.
        """
        log.info("Вызван метод chat (stream=%s)", stream)
        # Извлекаем API-ключ из конфигурации
        api_key = self.model_config.get("api_key")
        all_opts = self.model_config.get('generation', {}).copy()
        all_opts.update(self.model_config.get('inference', {}))
        all_opts.update(kwargs)
        all_opts.pop('stream', None)

        payload = self.provider.prepare_payload(
            messages, self.model, stream=stream, **all_opts
        )
        log.debug("--- Финальный Payload ---\n%s", payload)

        return self.provider.send_request(payload,api_key=api_key)