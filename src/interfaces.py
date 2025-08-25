from abc import ABC, abstractmethod
from typing import Dict, Any, Iterable, Union, List, Optional, Tuple


class ILLMClient(ABC):
    """
    Абстрактный интерфейс для всех LLM клиентов.
    Обеспечивает единообразный API для различных типов клиентов.
    """

    @abstractmethod
    def query(self, user_prompt: str) -> Dict[str, Any]:  # <-- ИЗМЕНЕНИЕ ЗДЕСЬ
        """
        Отправляет запрос к LLM и возвращает СТРУКТУРИРОВАННЫЙ ответ.

        Args:
            user_prompt: Промпт для отправки в LLM

        Returns:
            Словарь с ответом от LLM. Должен иметь следующую структуру:
            {
                "thinking_response": "Рассуждения модели...", # (может быть пустой строкой)
                "llm_response": "Финальный ответ модели"   # (может быть пустой строкой)
            }

        Raises:
            LLMClientError: При ошибках взаимодействия с LLM
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Возвращает информацию о модели.
        
        Returns:
            Словарь с информацией о модели (название, параметры, etc.)
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Возвращает название модели.
        
        Returns:
            Название модели
        """
        pass


class ProviderClient(ABC):
    """
    Абстрактный базовый класс для клиентов провайдеров языковых моделей.

    Определяет контракт, которому должны следовать все конкретные клиенты
    провайдеров, такие как OpenAI, Anthropic, Gemini и т.д. Этот интерфейс
    обеспечивает полную независимость LLMClient от деталей реализации
    конкретного API.
    """

    @abstractmethod
    def prepare_payload(
            self,
            messages: List[Dict[str, str]],
            model: str,
            *,
            stream: bool = False,
            **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Собирает тело запроса (payload) для API провайдера.

        Args:
            messages: Список сообщений в универсальном формате.
            model: Имя модели.
            stream: Включить ли потоковую передачу.
            **kwargs: Дополнительные параметры для модели (temperature, max_tokens и др.).

        Returns:
            Словарь, представляющий JSON-тело запроса.
        """
        ...

    @abstractmethod
    def send_request(
            self,
            payload: Dict[str, Any],
            api_key: Optional[str]
    ) -> Union[Dict[str, Any], Iterable[Dict[str, Any]]]:
        """
        Отправляет подготовленный payload на эндпоинт API.

        Args:
            payload: Тело запроса, созданное `prepare_payload`.

        Returns:
            - Если stream=False: Полный JSON-ответ в виде словаря.
            - Если stream=True: Итератор по чанкам ответа (каждый чанк - словарь).
        """
        ...

    @abstractmethod
    def extract_choices(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Извлекает список "ответов" (choices) из полного JSON-ответа.

        Args:
            response: Полный JSON-ответ от API.

        Returns:
            Список объектов-ответов.
        """
        ...

    @abstractmethod
    def extract_content_from_choice(self, choice: Dict[str, Any]) -> str:
        """
        Извлекает текстовое содержимое из одного "ответа" (choice) в не-потоковом режиме.

        Args:
            choice: Один элемент из списка, возвращенного `extract_choices`.

        Returns:
            Строка с текстом ответа.
        """
        ...

    @abstractmethod
    def extract_delta_from_chunk(self, chunk: Dict[str, Any]) -> Tuple[str, Optional[Dict], Optional[str]]:
        """
        Извлекает данные из одного чанка в потоковом режиме.

        Этот метод должен парсить чанк ответа от API и извлекать из него:
        - фрагмент текста (content)
        - информацию о вероятностях токенов (logprobs), если она есть
        - причину завершения генерации (finish_reason), если она указана

        Args:
            chunk: Один чанк (словарь) из итератора, возвращенного API.

        Returns:
            Кортеж (content, logprobs, finish_reason), где:
            - content (str): Фрагмент сгенерированного текста.
            - logprobs (Optional[Dict]): Словарь с данными logprobs или None.
            - finish_reason (Optional[str]): Строка с причиной завершения или None.
        """
        ...

    @abstractmethod
    def extract_metadata_from_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Извлекает метаданные (статистику) из полного не-потокового ответа."""
        ...

    @abstractmethod
    def extract_metadata_from_chunk(self, chunk: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Извлекает метаданные, если они пришли в финальном чанке потока.
        Возвращает словарь или None, если это не финальный чанк.
        """
        ...


class LLMClientError(Exception):
    """Базовое исключение для ошибок LLM клиентов"""
    pass


class LLMConfigurationError(LLMClientError):
    """Ошибка, связанная с неверной конфигурацией или несовместимыми параметрами."""
    pass


class LLMTimeoutError(LLMClientError):
    """Исключение для таймаутов запросов к LLM"""
    pass


class LLMConnectionError(LLMClientError):
    """Исключение для ошибок подключения к LLM"""
    pass


class LLMResponseError(LLMClientError):
    """Исключение для ошибок в ответе LLM"""
    pass

class LLMRequestError(LLMClientError):
    """Ошибка запроса к LLM (4xx, 5xx)"""
    def __init__(self, message, status_code=None, response_text=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
