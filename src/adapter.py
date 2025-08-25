import logging
import re
import time
from typing import Dict, Any, Generator

from src.interfaces import ILLMClient, LLMClientError
from src.llm_client import LLMClient

log = logging.getLogger(__name__)


class AdapterLLMClient(ILLMClient):
    """
    Класс-адаптер. Служит "мостом" между новым LLMClient и старым
    интерфейсом ILLMClient, который ожидает TestRunner.
    Отвечает за сборку ответа, парсинг "мыслей" и сбор метрик.
    """

    def __init__(self, new_llm_client: LLMClient, model_config: Dict[str, Any]):
        self.new_client = new_llm_client
        self.model_config = model_config
        self.query_timeout = int(model_config.get('options', {}).get('query_timeout', 180))

    def get_model_name(self) -> str:
        return self.new_client.model

    def get_model_info(self) -> Dict[str, Any]:
        return {"model_name": self.new_client.model, "provider": self.new_client.provider.__class__.__name__}

    @staticmethod
    def _parse_think_response(self, raw_response: str) -> Dict[str, Any]:
        think_pattern = re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE)
        think_match = think_pattern.search(raw_response)

        thinking_response, llm_response = "", raw_response
        if think_match:
            thinking_response = think_match.group(1).strip()
            llm_response = think_pattern.sub("", raw_response).strip()

        return {"thinking_response": thinking_response, "llm_response": llm_response}

    # Сначала определим эвристическую функцию. Ее можно сделать статическим методом.
    @staticmethod
    def _estimate_tokens_heuristic(text: str) -> int:
        if not text: return 0
        return int(len(text) / 4.0) + 1

    def _count_tokens_client(self, text: str) -> int | None:
        if getattr(self, 'tokenizer', None):
            log.warning(f"Используется эвристика.")
            return self._estimate_tokens_heuristic(text)
        else:
            # Не логируем здесь, чтобы не спамить, если токенизатор не настроен
            return self._estimate_tokens_heuristic(text)

    # Эти методы должны быть внутри вашего класса Adapter
    def _handle_stream_response(self, response_generator: Generator) -> tuple[
        str, dict, float | None, float]:
        """Обрабатывает потоковый ответ, собирая текст, "мышление" и метаданные."""
        log.info("Начало получения потокового ответа...")
        print(">>> LLM Stream: ", end="", flush=True)

        # Переменные для сбора данных
        full_content_parts = []
        final_logprobs = None
        final_finish_reason = None
        server_metadata = {}

        # Переменные для таймингов
        ttft_time: float | None = None
        first_chunk = True

        for chunk_dict in response_generator:
            if first_chunk:
                ttft_time = time.perf_counter()
                first_chunk = False

            # 1. Извлекаем все данные из чанка с помощью нового метода
            content, logprobs, finish_reason = self.new_client.provider.extract_delta_from_chunk(chunk_dict)

            # 2. Обрабатываем текстовый контент
            if content:
                # Выводим в консоль в реальном времени
                print(content, end="", flush=True)
                full_content_parts.append(content)

            # 3. Агрегируем метаданные
            if logprobs:
                # Logprobs обычно приходят с каждым токеном.
                # Можно либо собирать их все в список, либо сохранять последние.
                # Для примера, просто обновим server_metadata.
                # В реальном приложении логика может быть сложнее.
                if 'logprobs' not in server_metadata:
                    server_metadata['logprobs'] = []
                server_metadata['logprobs'].append(logprobs)

            if finish_reason:
                # Причина завершения обычно приходит в последнем чанке
                final_finish_reason = finish_reason
                server_metadata['finish_reason'] = finish_reason

            # Сохраняем совместимость с вашим старым `extract_metadata_from_chunk`, если он нужен
            chunk_metadata = self.new_client.provider.extract_metadata_from_chunk(chunk_dict)
            if chunk_metadata:
                server_metadata.update(chunk_metadata)

        end_time = time.perf_counter()
        print("\n")

        # 4. Собираем итоговый результат
        final_response_str = "".join(full_content_parts)
        log.info("Потоковый ответ полностью получен (длина: %d символов).", len(final_response_str))
        if final_finish_reason:
            log.info("Причина завершения генерации: %s", final_finish_reason)


        return final_response_str, server_metadata, ttft_time, end_time

    def _handle_non_stream_response(self, response_dict: dict) -> tuple[str, dict, float, float]:
        """Обрабатывает непотоковый (полный) ответ."""
        end_time = ttft_time = time.perf_counter()

        choices = self.new_client.provider.extract_choices(response_dict)
        final_response_str = "".join(self.new_client.provider.extract_content_from_choice(c) for c in choices)
        server_metadata = self.new_client.provider.extract_metadata_from_response(response_dict)
        print(">>> LLM response: ", end="", flush=True)
        print(final_response_str)
        return final_response_str, server_metadata, ttft_time, end_time

    def _build_final_metrics(self, server_metadata: dict, prompt_token_count: int, final_response_str: str,
                             start_time: float, ttft_time: float | None, end_time: float) -> dict:
        """Собирает итоговые метрики, комбинируя серверные данные и клиентские замеры."""
        # Начинаем с того, что дал сервер
        final_metrics = server_metadata.copy()

        # Считаем токены ответа на клиенте (как фолбэк)
        if 'eval_count' not in final_metrics:
            eval_token_count_client = self._count_tokens_client(final_response_str)
            log.info(f"Клиентская оценка токенов ответа: {eval_token_count_client}")
            final_metrics['eval_count'] = eval_token_count_client

        # Используем подсчет токенов промпта как фолбэк
        if 'prompt_eval_count' not in final_metrics:
            final_metrics['prompt_eval_count'] = prompt_token_count

        # Если сервер не дал тайминги, считаем их сами
        if 'prompt_eval_duration' not in final_metrics:
            log.debug("Сервер не вернул детальные тайминги. Расчет на стороне клиента.")
            total_duration_ns = int((end_time - start_time) * 1e9)
            final_metrics['total_duration'] = total_duration_ns
            if ttft_time:
                final_metrics['prompt_eval_duration'] = int((ttft_time - start_time) * 1e9)
                final_metrics['eval_duration'] = int((end_time - ttft_time) * 1e9)
            else:
                final_metrics['prompt_eval_duration'] = total_duration_ns
                final_metrics['eval_duration'] = 0
            final_metrics['load_duration'] = 0

        # Безусловно добавляем уникальные клиентские метрики полного цикла
        total_latency_ms = (end_time - start_time) * 1000
        final_metrics['total_latency_ms'] = total_latency_ms
        if ttft_time:
            final_metrics['time_to_first_token_ms'] = round((ttft_time - start_time) * 1000, 2)
        else:
            final_metrics['time_to_first_token_ms'] = round(total_latency_ms, 2)

        return {k: v for k, v in final_metrics.items() if v is not None}

    def _build_error_response(self, error: Exception, start_time: float) -> Dict[str, Any]:
        """Формирует стандартизированный ответ об ошибке."""
        log.error("Произошла ошибка API при запросе к LLM: %s", error)
        total_time_ms = (time.perf_counter() - start_time) * 1000
        return {
            "final_response": f"ERROR: API call failed. Reason: {error}",
            "parsed_response": None,
            "performance_metrics": {
                "model": self.model_config.get('model_name', 'unknown'),
                "total_latency_ms": total_time_ms,
                "error": str(error)
            }
        }

    def query(self, user_prompt: str) -> Dict[str, Any]:
        log.info("Adapter получил промпт (длина: %d символов).", len(user_prompt))
        prompt_token_count = self._count_tokens_client(user_prompt)
        log.info(f"Клиентская оценка токенов промпта: {prompt_token_count}")

        messages = [{"role": "user", "content": user_prompt}]
        inference_opts = self.model_config.get('inference', {})
        use_stream = str(inference_opts.get('stream', 'false')).lower() == 'true'
        generation_opts = self.model_config.get('generation', {})

        start_time = time.perf_counter()

        try:
            response_or_stream = self.new_client.chat(
                messages, stream=use_stream, **generation_opts
            )

            if use_stream and isinstance(response_or_stream, Generator):
                final_response_str, server_metadata, ttft_time, end_time = self._handle_stream_response(
                    response_or_stream)
            elif not use_stream and isinstance(response_or_stream, dict):
                final_response_str, server_metadata, ttft_time, end_time = self._handle_non_stream_response(
                    response_or_stream)
            else:
                # Обработка неожиданного типа ответа
                raise TypeError(
                    f"Получен неожиданный тип ответа: {type(response_or_stream)} для use_stream={use_stream}")

            final_metrics = self._build_final_metrics(
                server_metadata=server_metadata,
                prompt_token_count=prompt_token_count,
                final_response_str=final_response_str,
                start_time=start_time,
                ttft_time=ttft_time,
                end_time=end_time
            )

            parsed_struct = self._parse_think_response(final_response_str)
            parsed_struct['performance_metrics'] = final_metrics
            return parsed_struct

        except LLMClientError as e:  # Замените на ваше реальное исключение
            return self._build_error_response(e, start_time)
