# src/feedback_sender.py

import logging
from typing import Dict, Any

import requests

# Константы для API
FEEDBACK_API_URL = "https://aipromptsapi.vercel.app/api/feedback"
HEADERS = {"Content-Type": "application/json"}

logger = logging.getLogger(__name__)

def send_feedback(content: str, app_info: Dict[str, Any]) -> bool:
    """
    Отправляет сообщение обратной связи на сервер.

    Args:
        content: Текст сообщения от пользователя.
        app_info: Словарь с информацией о приложении
                  (name, id, version, packagename).

    Returns:
        True, если сообщение успешно отправлено, иначе False.
    """
    payload = {
        "appname": app_info,
        "content": content
    }

    logger.info(f"Отправка обратной связи на {FEEDBACK_API_URL}")
    logger.debug(f"Payload: {payload}")

    try:
        response = requests.post(
            FEEDBACK_API_URL,
            json=payload,
            headers=HEADERS,
            timeout=15  # Таймаут в 15 секунд
        )
        # Проверяем, был ли ответ успешным (статус код 2xx)
        response.raise_for_status()
        logger.info("Обратная связь успешно отправлена.")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при отправке обратной связи: {e}", exc_info=True)
        return False

