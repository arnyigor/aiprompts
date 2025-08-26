# src/sync_manager.py
import hashlib
import json
import logging
import requests
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple, Callable

from llm_settings import Settings
from models import Prompt
from storage import LocalStorage

# Прямая, постоянная ссылка на скачивание архива.
# Этот URL не использует API и не тратит лимиты.
PROMPTS_DOWNLOAD_URL = (
    "https://github.com/arnyigor/aiprompts/releases/download/latest-prompts/prompts.zip"
)


class SyncManager:
    """
    Управляет синхронизацией, используя прямую ссылку на архив релиза,
    чтобы избежать проблем с лимитами GitHub API.
    """

    def __init__(
            self,
            storage: LocalStorage,
            settings: Settings,
            progress_cb: Callable[[str], None] = None,
            log_cb: Callable[[str], None] = None,
    ):
        self.logger = logging.getLogger(__name__)
        self.storage = storage
        self.settings = settings
        self.prompts_dir = storage.storage_path
        self._progress_cb = progress_cb or (lambda _msg: None)
        self._log_cb = log_cb or (lambda _msg: None)

    def _emit(self, msg: str):
        self._progress_cb(msg)

    def _log(self, msg: str):
        self.logger.debug(msg)
        self._log_cb(msg)

    def sync(self) -> Tuple[int, int, int]:
        """Выполняет полный цикл синхронизации."""
        self._log("--- Начинаем сеанс синхронизации библиотеки промптов ---")
        try:
            with tempfile.TemporaryDirectory() as temp_dir_str:
                temp_path = Path(temp_dir_str)
                archive_path = temp_path / "prompts.zip"
                unpacked_path = temp_path / "unpacked"

                # --- УПРОЩЕННЫЙ ШАГ СКАЧИВАНИЯ ---
                self._emit("Скачиваем архив с промптами...")
                self._log(f"✓ URL для скачивания: {PROMPTS_DOWNLOAD_URL}")
                self._download_file(PROMPTS_DOWNLOAD_URL, archive_path)
                self._log("✓ Архив успешно скачан.")

                self._emit("Распаковываем архив...")
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(unpacked_path)

                remote_root = unpacked_path / "prompts"
                if not remote_root.exists():
                    msg = "Архив не содержит ожидаемую папку 'prompts'."
                    self._log(f"❌ Ошибка: {msg}")
                    raise FileNotFoundError(msg)

                self._log(f"✓ Архив распакован во временную директорию.")

                self._emit("Анализируем изменения...")
                self._log("\nИндексируем удаленные файлы (из архива)...")
                remote_index = self._build_index_from_path(remote_root, use_settings=False)
                self._log(f"→ Найдено удаленных файлов: {len(remote_index)}")

                self._log("\nИндексируем локальные файлы...")
                local_index = self._build_index_from_path(self.prompts_dir, use_settings=True)
                self._log(f"→ Найдено локальных файлов: {len(local_index)}")

                self._emit("Применяем изменения...")
                new, upd, delt = self._apply_changes(local_index, remote_index)

                self._log("\n--- Сводка по синхронизации ---")
                self._log(f"✓ Новых файлов: {new}")
                self._log(f"✓ Обновлено файлов: {upd}")
                self._log(f"✓ Удалено файлов: {delt}")
                self._log("--- Сеанс синхронизации успешно завершен ---")

                return new, upd, delt

        except requests.HTTPError as e:
            if e.response.status_code == 404:
                self.logger.error("Ошибка 404: архив 'prompts.zip' не найден в релизе 'latest-prompts'.")
                self._log("\n❌ ОШИБКА: Не удалось найти архив с промптами на GitHub. Возможно, релиз еще не создан.")
            else:
                self.logger.error("Ошибка сети при скачивании: %s", e, exc_info=True)
                self._log(f"\n❌ ОШИБКА СЕТИ: Не удалось скачать архив. Проверьте подключение.")
            raise e
        except Exception as e:
            self.logger.exception("Непредвиденная ошибка во время синхронизации:")
            self._log(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
            raise e

    def _download_file(self, url: str, target_path: Path):
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status() # Вызовет HTTPError для 4xx/5xx кодов (например, 404 Not Found)
            with open(target_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

    def _build_index_from_path(self, base_path: Path, use_settings: bool = False) -> Dict[str, Dict[str, Any]]:
        # ... (этот метод остается без изменений) ...
        index = {}
        if not base_path.exists():
            return {}
        for file_path in base_path.rglob("*.json"):
            rel_path = str(file_path.relative_to(base_path)).replace("\\", "/")
            prompt_id = file_path.stem
            try:
                mtime = file_path.stat().st_mtime
                with file_path.open("rb") as f:
                    content = f.read()
                    header = f"blob {len(content)}\0".encode('utf-8')
                    sha = hashlib.sha1(header + content).hexdigest()
                if use_settings:
                    is_local_flag = self.settings.is_local(prompt_id)
                    is_favorite_flag = self.settings.is_favorite(prompt_id)
                else:
                    data = json.loads(content.decode('utf-8'))
                    is_local_flag = data.get("is_local", False)
                    is_favorite_flag = data.get("is_favorite", False)
                index[rel_path] = { "sha": sha, "path": file_path, "mtime": mtime, "is_local": is_local_flag, "is_favorite": is_favorite_flag, }
            except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
                self._log(f"  ! Не удалось прочитать файл {file_path}: {e}")
        return index

    def _apply_changes(self, local_index: Dict, remote_index: Dict) -> Tuple[int, int, int]:
        # ... (этот метод остается без изменений, он уже идеален) ...
        new_count, updated_count, deleted_count = 0, 0, 0
        local_paths = set(local_index.keys())
        remote_paths = set(remote_index.keys())

        # 1. Новые файлы
        self._log("\n→ Проверяем новые файлы...")
        for rel_path in remote_paths - local_paths:
            self._log(f"  + Сохраняем новый файл: {rel_path}")
            source_file = remote_index[rel_path]["path"]
            prompt_data = json.loads(source_file.read_text(encoding="utf-8"))
            if "created_at" in prompt_data and isinstance(prompt_data["created_at"], str): prompt_data["created_at"] = datetime.fromisoformat(prompt_data["created_at"])
            if "updated_at" in prompt_data and isinstance(prompt_data["updated_at"], str): prompt_data["updated_at"] = datetime.fromisoformat(prompt_data["updated_at"])
            prompt_obj = Prompt.model_validate(prompt_data)
            self.storage.save_prompt(prompt_obj)
            new_count += 1

        # 2. Удаленные файлы
        self._log("\n→ Проверяем удаленные файлы...")
        for rel_path in local_paths - remote_paths:
            l_meta = local_index[rel_path]
            if not l_meta.get("is_local", False):
                prompt_id = l_meta["path"].stem
                self._log(f"  - Удаляем старый файл: {rel_path}")
                try:
                    self.storage.delete_prompt(prompt_id)
                    deleted_count += 1
                except (ValueError, FileNotFoundError) as e:
                    self._log(f"    ! Не удалось удалить файл {prompt_id}: {e}")
            else:
                self._log(f"  → Пропускаем удаление, файл помечен как локальный: {rel_path}")

        # 3. Общие файлы
        self._log("\n→ Проверяем обновления...")
        for rel_path in local_paths & remote_paths:
            l_meta = local_index[rel_path]
            r_meta = remote_index[rel_path]
            if l_meta["sha"] == r_meta["sha"]: continue
            if l_meta.get("is_local", False): continue
            if l_meta["mtime"] > r_meta["mtime"]: continue
            self._log(f"  Δ Обновляем файл до последней версии: {rel_path}")
            source_file = r_meta["path"]
            prompt_data = json.loads(source_file.read_text(encoding="utf-8"))
            if "created_at" in prompt_data and isinstance(prompt_data["created_at"], str): prompt_data["created_at"] = datetime.fromisoformat(prompt_data["created_at"])
            if "updated_at" in prompt_data and isinstance(prompt_data["updated_at"], str): prompt_data["updated_at"] = datetime.fromisoformat(prompt_data["updated_at"])
            prompt_obj = Prompt.model_validate(prompt_data)
            prompt_obj.is_local = l_meta.get("is_local", False)
            prompt_obj.is_favorite = l_meta.get("is_favorite", False)
            self.storage.save_prompt(prompt_obj)
            updated_count += 1

        return new_count, updated_count, deleted_count