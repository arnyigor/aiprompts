# src/sync_manager.py
import hashlib
import json
import logging
import requests
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Any, Tuple, Callable

# Постоянная ссылка на "живой" релиз, содержащий последнюю версию промптов.
# ВАЖНО: Убедитесь, что репозиторий и имя владельца указаны верно.
PROMPTS_RELEASE_URL = (
    "https://api.github.com/repos/arnyigor/aiprompts/releases/tags/latest-prompts"
)


class SyncManager:
    """
    Управляет синхронизацией локальных файлов с удаленным репозиторием GitHub,
    используя стратегию загрузки единого архива из релиза.
    """

    def __init__(
            self,
            prompts_dir: Path,
            progress_cb: Callable[[str], None] = None,
            log_cb: Callable[[str], None] = None
    ):
        """
        Инициализирует менеджер синхронизации.

        Args:
            prompts_dir: Путь к локальной директории с промптами.
            progress_cb: Callback для основных этапов.
            log_cb: Callback для детальных лог-сообщений.
        """
        self.logger = logging.getLogger(__name__)
        self.prompts_dir = prompts_dir
        self._progress_cb = progress_cb or (lambda _msg: None)
        self._log_cb = log_cb or (lambda _msg: None)

    def _emit(self, msg: str):
        """Вызывает callback для обновления статуса основного этапа."""
        self._progress_cb(msg)

    def _log(self, msg: str):
        """Вызывает callback для отправки детального лог-сообщения."""
        self.logger.debug(msg)
        self._log_cb(msg)

    def sync(self) -> Tuple[int, int, int]:
        """
        Выполняет полный цикл синхронизации.

        Returns:
            Кортеж с количеством (новых, обновленных, удаленных) файлов.
        """
        self._log("--- Начинаем сеанс синхронизации библиотеки промптов ---")

        try:
            # 1. Получить URL архива из стабильного релиза
            self._emit("Получаем информацию о библиотеке...")
            response = requests.get(PROMPTS_RELEASE_URL, timeout=20)
            response.raise_for_status()
            release_info = response.json()

            if not release_info.get('assets'):
                msg = "В релизе 'latest-prompts' не найден архив с промптами."
                self._log(f"❌ Ошибка: {msg}")
                raise FileNotFoundError(msg)

            asset_url = release_info['assets'][0]['browser_download_url']
            self._log(f"✓ URL для скачивания архива: {asset_url}")

            # Используем временную директорию, которая автоматически очистится
            with tempfile.TemporaryDirectory() as temp_dir_str:
                temp_path = Path(temp_dir_str)
                archive_path = temp_path / "prompts.zip"
                unpacked_path = temp_path / "unpacked"

                # 2. Скачать архив
                self._emit("Скачиваем архив с промптами...")
                self._download_file(asset_url, archive_path)
                self._log("✓ Архив успешно скачан.")

                # 3. Распаковать архив
                self._emit("Распаковываем архив...")
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(unpacked_path)

                # Архив содержит папку 'prompts', поэтому реальный корень данных - внутри
                remote_root = unpacked_path / "prompts"
                if not remote_root.exists():
                    msg = "Скачанный архив не содержит ожидаемую папку 'prompts'."
                    self._log(f"❌ Ошибка: {msg}")
                    raise FileNotFoundError(msg)

                self._log(f"✓ Архив распакован во временную директорию.")

                # 4. Построить индексы и сравнить
                self._emit("Анализируем изменения...")
                self._log("\nИндексируем удаленные файлы (из архива)...")
                remote_index = self._build_index_from_path(remote_root)
                self._log(f"→ Найдено удаленных файлов: {len(remote_index)}")

                self._log("\nИндексируем локальные файлы...")
                local_index = self._build_index_from_path(self.prompts_dir)
                self._log(f"→ Найдено локальных файлов: {len(local_index)}")

                # 5. Применить изменения
                self._emit("Применяем изменения...")
                new, upd, delt = self._apply_changes(local_index, remote_index, remote_root)

                self._log("\n--- Сводка по синхронизации ---")
                self._log(f"✓ Новых файлов: {new}")
                self._log(f"✓ Обновлено файлов: {upd}")
                self._log(f"✓ Удалено файлов: {delt}")
                self._log("--- Сеанс синхронизации успешно завершен ---")

                return new, upd, delt

        except requests.RequestException as e:
            self.logger.error("Ошибка сети при синхронизации: %s", e, exc_info=True)
            self._log(f"\n❌ ОШИБКА СЕТИ: Не удалось связаться с GitHub. Проверьте подключение.")
            raise ConnectionError(f"Ошибка сети: {e}") from e
        except (FileNotFoundError, zipfile.BadZipFile) as e:
            self.logger.error("Ошибка обработки архива: %s", e, exc_info=True)
            self._log(f"\n❌ ОШИБКА ФАЙЛА: Не удалось обработать архив с промптами.")
            raise e
        except Exception as e:
            self.logger.exception("Непредвиденная ошибка во время синхронизации:")
            self._log(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
            raise e

    def _download_file(self, url: str, target_path: Path):
        """Скачивает файл в потоковом режиме, экономя память."""
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(target_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

    def _build_index_from_path(self, base_path: Path) -> Dict[str, Dict[str, Any]]:
        """Создает индекс файлов из указанной директории."""
        index = {}
        if not base_path.exists():
            return {}

        for file_path in base_path.rglob("*.json"):
            rel_path = str(file_path.relative_to(base_path)).replace("\\", "/")
            try:
                with file_path.open("rb") as f:
                    content = f.read()
                    header = f"blob {len(content)}\0".encode('utf-8')
                    sha = hashlib.sha1(header + content).hexdigest()

                # Для локальных файлов также читаем метаданные
                data = json.loads(content.decode('utf-8'))
                index[rel_path] = {
                    "sha": sha,
                    "path": file_path, # Абсолютный путь к источнику
                    "is_favorite": data.get("is_favorite", False),
                    "is_local": data.get("is_local", False),
                }
            except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
                self._log(f"  ! Не удалось прочитать файл {file_path}: {e}")
        return index

    def _apply_changes(
            self, local_index: Dict, remote_index: Dict, remote_root: Path
    ) -> Tuple[int, int, int]:
        """Сравнивает индексы и применяет изменения (копирует/удаляет файлы)."""
        new_count, updated_count, deleted_count = 0, 0, 0

        local_paths = set(local_index.keys())
        remote_paths = set(remote_index.keys())

        # 1. Новые файлы (есть в remote, нет в local)
        self._log("\n→ Проверяем новые файлы...")
        for rel_path in remote_paths - local_paths:
            self._log(f"  + Копируем новый файл: {rel_path}")
            source_file = remote_index[rel_path]["path"]
            target_file = self.prompts_dir / rel_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, target_file)
            new_count += 1

        # 2. Удаленные файлы (есть в local, нет в remote)
        self._log("\n→ Проверяем удаленные файлы...")
        for rel_path in local_paths - remote_paths:
            if not local_index[rel_path].get("is_local", False):
                self._log(f"  - Удаляем старый файл: {rel_path}")
                local_index[rel_path]["path"].unlink(missing_ok=True)
                deleted_count += 1
            else:
                self._log(f"  → Пропускаем удаление локального файла: {rel_path}")

        # 3. Измененные файлы (есть и там, и там)
        self._log("\n→ Проверяем обновления...")
        for rel_path in local_paths & remote_paths:
            l_meta = local_index[rel_path]
            r_meta = remote_index[rel_path]

            if l_meta["sha"] == r_meta["sha"]:
                continue # Файлы идентичны

            if l_meta.get("is_local", False):
                self._log(f"  → Пропускаем обновление локального файла: {rel_path}")
                continue

            self._log(f"  Δ Обновляем файл: {rel_path}")

            # Аккуратно обновляем, сохраняя флаг is_favorite
            source_file = r_meta["path"]
            target_file = l_meta["path"]

            # Читаем новый контент
            new_data = json.loads(source_file.read_text(encoding="utf-8"))
            # Сохраняем пользовательский флаг
            new_data["is_favorite"] = l_meta.get("is_favorite", False)

            # Записываем обновленный файл
            target_file.write_text(
                json.dumps(new_data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            updated_count += 1

        return new_count, updated_count, deleted_count