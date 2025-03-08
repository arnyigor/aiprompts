# data/storage.py
import logging
from pathlib import Path
from typing import List, Optional

from models import Prompt


class LocalStorage:
    def __init__(self, base_path: str = "prompts"):
        self.logger = logging.getLogger(__name__)
        self.storage_path = Path(base_path)
        self.storage_path.mkdir(exist_ok=True)
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_prompt(self, prompt: Prompt):
        try:
            """Сохранение промпта в JSON файл с версионированием"""
            file_path = self.storage_path / f"{prompt.id}.json"

            # Получаем JSON-строку напрямую из модели
            json_data = prompt.model_dump_json(indent=2)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json_data)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения промпта {str(e)}", exc_info=True)

    def load_prompt(self, prompt_id: str) -> Optional[Prompt]:
        """Прямая загрузка из файла по ID"""
        file_path = self.base_path / f"{prompt_id}.json"
        if not file_path.exists():
            return None

        try:
            # Чтение файла как бинарных данных
            raw_data = file_path.read_bytes()

            # Попытка декодирования через UTF-8 с заменой ошибок
            content = raw_data.decode('utf-8', errors='replace')

            # Замена проблемных символов
            cleaned_content = content.replace('\ufffd', '')  # Удаляем символы замены
            cleaned_content = cleaned_content.replace('\x98', '')  # Удаляем специфичный байт

            # Автоматическое пересохранение файла в правильной кодировке
            self._resave_if_needed(file_path, raw_data, cleaned_content)
            return Prompt.model_validate_json(cleaned_content)
        except Exception as e:
            self.logger.error(f"Ошибка загрузки {prompt_id}: {str(e)}")
            return None

    # storage.py
    def list_prompts(self) -> List[Prompt]:
        prompts = []
        for file_path in self.base_path.glob("*.json"):
            try:
                # Чтение файла как бинарных данных
                raw_data = file_path.read_bytes()

                # Попытка декодирования через UTF-8 с заменой ошибок
                content = raw_data.decode('utf-8', errors='replace')

                # Замена проблемных символов
                cleaned_content = content.replace('\ufffd', '')  # Удаляем символы замены
                cleaned_content = cleaned_content.replace('\x98', '')  # Удаляем специфичный байт

                prompt = Prompt.model_validate_json(cleaned_content)
                prompts.append(prompt)

                # Автоматическое пересохранение файла в правильной кодировке
                self._resave_if_needed(file_path, raw_data, cleaned_content)

            except Exception as e:
                self.logger.error(f"Ошибка в {file_path.name}: {str(e)}")

        return prompts

    def _resave_if_needed(self, file_path: Path, original_data: bytes, cleaned_content: str):
        """Пересохраняет файл, если обнаружены проблемы с кодировкой"""
        try:
            # Сравниваем оригинальные данные с очищенными
            if original_data != cleaned_content.encode('utf-8'):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                self.logger.info(f"Файл {file_path.name} автоматически пересохранен в UTF-8")
        except Exception as e:
            self.logger.warning(f"Не удалось пересохранить {file_path.name}: {str(e)}")

    def delete_prompt(self, prompt_id: str):
        """Удаляет промпт по ID"""
        file_path = self.base_path / f"{prompt_id}.json"
        if file_path.exists():
            file_path.unlink()
        else:
            raise FileNotFoundError(f"Промпт {prompt_id} не найден")
