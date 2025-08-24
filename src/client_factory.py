import logging
from typing import Dict, Any

from src.interfaces import ProviderClient
from src.ollama_client import OllamaClient
from src.openai_client import OpenAICompatibleClient

logger = logging.getLogger(__name__)


class LLMClientFactory:
    """
    Простая фабрика: сравнение только со строковым client_type из model_config.
    Классы не храним в мапах, создаём на месте. Дефолты — внутри веток.
    """

    @staticmethod
    def create_provider(model_config: Dict[str, Any]) -> ProviderClient:
        raw_ct = model_config.get("client_type")
        if not raw_ct:
            raise ValueError(f"Для модели '{model_config.get('name')}' не указан 'client_type'.")

        client_type = str(raw_ct).strip().lower()
        name = model_config.get("name")

        logger.info("  🔧 Создаем провайдера '%s' для модели '%s'...", client_type, name)

        # Нормализованные параметры
        api_base = model_config.get("api_base")
        api_key = model_config.get("api_key")

        # === Ветвление строго по строке ===
        if client_type == "ollama":
            # Ollama API (не OpenAI-совместимый). Дефолт: 11434 без /v1.
            api_base = "http://localhost:11434"
            logger.info("   - Класс: OllamaClient, URL: %s", api_base)
            # Если ваш OllamaClient поддерживает base_url — передаем; иначе уберите аргумент.
            return OllamaClient()

        elif client_type == "lmstudio":
            # OpenAI-совместимый. Дефолт: 1234 с /v1.
            api_base = "http://127.0.0.1:1234/v1"
            logger.info("   - Класс: OpenAICompatibleClient, URL: %s", api_base)
            return OpenAICompatibleClient(api_key=api_key, base_url=api_base)

        elif client_type == "jan":
            # OpenAI-совместимый. Дефолт: 1337 с /v1. <-- ВАЖНО: не 11434!
            api_base = "http://127.0.0.1:1337/v1"
            logger.info("   - Класс: OpenAICompatibleClient, URL: %s", api_base)
            return OpenAICompatibleClient(api_key=api_key, base_url=api_base)

        elif client_type == "openai_compatible":
            # Универсальный OpenAI-совместимый: обязателен api_base.
            if not api_base:
                raise ValueError(
                    f"Для 'openai_compatible' модели '{name}' должен быть указан 'api_base'."
                )
            logger.info("   - Класс: OpenAICompatibleClient, URL: %s", api_base)
            return OpenAICompatibleClient(api_key=api_key, base_url=api_base, )

        else:
            raise ValueError(
                f"Неизвестный тип клиента: '{client_type}'. "
                f"Ожидается один из: 'ollama', 'lmstudio', 'jan', 'openai_compatible', 'gemini'."
            )
