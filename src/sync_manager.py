# src/sync_manager.py
import hashlib
import json
import logging
import requests
from pathlib import Path
from typing import Dict, Any, Tuple, Callable, List

# Константа для URL API GitHub
GITHUB_API_URL = (
    "https://api.github.com/repos/arnyigor/aiprompts/contents/prompts"
)


class SyncManager:
    """
    Управляет синхронизацией локальных файлов с удаленным репозиторием GitHub.
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
            progress_cb: Callback для основных этапов (отображается вверху диалога).
            log_cb: Callback для детальных сообщений (добавляются в текстовое поле лога).
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
        self.logger.debug(msg)  # Также дублируем в основной логгер приложения
        self._log_cb(msg)

    def sync(self) -> Tuple[int, int, int]:
        """
        Выполняет полный цикл синхронизации.

        Returns:
            Кортеж с количеством (новых, обновленных, удаленных) файлов.
        """
        self.logger.info("--- Синхронизация началась ---")
        self._log("--- Начинаем сеанс синхронизации ---")

        try:
            self._emit("Получаем индекс с GitHub…")
            remote_index = self.fetch_remote_index()
            self._log(f"✓ Получен индекс с GitHub: {len(remote_index)} файлов.")

            self._emit("Индексируем локальные файлы…")
            local_index = self._build_local_index()
            self._log(f"✓ Проиндексированы локальные файлы: {len(local_index)} найдено.")

            self._emit("Сравниваем файлы…")
            new_cnt, deleted_cnt = self._sync_new_and_deleted(remote_index, local_index)
            self._log(f"→ Новых файлов для скачивания: {new_cnt}")
            self._log(f"→ Файлов для удаления: {deleted_cnt}")

            self._emit("Обновляем измененные файлы…")
            upd_cnt = self._sync_modified(remote_index, local_index)
            self._log(f"→ Файлов для обновления: {upd_cnt}")

            self.logger.info("--- Синхронизация завершена ---")
            self._emit("Синхронизация успешно завершена!")
            self._log("\n--- Сеанс синхронизации успешно завершен ---")
            return new_cnt, upd_cnt, deleted_cnt

        except requests.RequestException as e:
            self.logger.error("Ошибка сети при синхронизации: %s", e, exc_info=True)
            self._log(f"\n❌ ОШИБКА СЕТИ: Не удалось связаться с сервером GitHub. Проверьте подключение к интернету.")
            self._log(f"   Детали: {e}")
            raise ConnectionError(f"Ошибка сети: {e}") from e
        except Exception as e:
            self.logger.exception("Непредвиденная ошибка во время синхронизации:")
            self._log(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: Произошла непредвиденная ошибка.")
            self._log(f"   Детали: {e}")
            raise e

    def _build_local_index(self) -> Dict[str, Dict[str, Any]]:
        """Создает индекс локальных файлов, вычисляя их SHA1 хэши."""
        index = {}
        if not self.prompts_dir.exists():
            self._log("! Локальная директория не найдена, создаем...")
            self.prompts_dir.mkdir(parents=True)
            return {}

        for file_path in self.prompts_dir.rglob("*.json"):
            # Нормализуем путь для консистентности (Linux-style)
            rel_path = str(file_path.relative_to(self.prompts_dir)).replace("\\", "/")
            try:
                with file_path.open("rb") as f:
                    content = f.read()
                    # Git вычисляет SHA1 не от чистого файла, а от заголовка "blob <size>\0" + контент
                    header = f"blob {len(content)}\0".encode('utf-8')
                    sha = hashlib.sha1(header + content).hexdigest()

                data = json.loads(content.decode('utf-8'))
                index[rel_path] = {
                    "sha": sha,
                    "path": file_path,
                    "is_favorite": data.get("is_favorite", False),
                    "is_local": data.get("is_local", False),
                }
            except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
                self._log(f"  ! Не удалось прочитать локальный файл {file_path}: {e}")
        return index

    def _sync_new_and_deleted(
            self, remote: Dict, local: Dict
    ) -> Tuple[int, int]:
        """Скачивает новые файлы и удаляет те, что исчезли из репозитория."""
        new_count = 0
        deleted_count = 0

        self._log("\nЭтап 1: Поиск новых файлов...")
        remote_paths = set(remote.keys())
        local_paths = set(local.keys())

        for rel_path in remote_paths - local_paths:
            self._log(f"  + Найден новый файл: {rel_path}")
            self._download(rel_path, remote[rel_path]["url"])
            new_count += 1

        self._log("\nЭтап 2: Поиск удаленных файлов...")
        for rel_path in local_paths - remote_paths:
            l_meta = local[rel_path]
            if not l_meta.get("is_local", False):
                self._log(f"  - Файл удален в репозитории: {rel_path}")
                l_meta["path"].unlink(missing_ok=True)
                deleted_count += 1
            else:
                self._log(f"  → Пропускаем удаление локального файла: {rel_path}")

        return new_count, deleted_count

    def _sync_modified(self, remote: Dict, local: Dict) -> int:
        """Обновляет локальные файлы, если их SHA отличается от удаленных."""
        updated_count = 0
        self._log("\nЭтап 3: Проверка обновлений для существующих файлов...")

        # Проверяем только те файлы, которые есть и локально, и удаленно
        common_paths = set(remote.keys()) & set(local.keys())

        for rel_path in common_paths:
            l_meta = local[rel_path]
            r_meta = remote[rel_path]

            if l_meta.get("is_local", False):
                self._log(f"  → Пропускаем локальный файл: {rel_path}")
                continue

            if l_meta["sha"] == r_meta["sha"]:
                continue  # Файлы идентичны

            self._log(f"  Δ Обновляем измененный файл: {rel_path}")
            self._log(f"    (локальный SHA: {l_meta['sha'][:7]}, удаленный SHA: {r_meta['sha'][:7]})")

            try:
                response = requests.get(r_meta["url"], timeout=20)
                response.raise_for_status()
                fresh_data = response.json()

                # Сохраняем пользовательский флаг "избранное"
                fresh_data["is_favorite"] = l_meta.get("is_favorite", False)

                target_path = self.prompts_dir / rel_path
                target_path.write_text(
                    json.dumps(fresh_data, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
                updated_count += 1
            except requests.RequestException as e:
                self._log(f"  ! Ошибка при обновлении файла {rel_path}: {e}")
            except json.JSONDecodeError:
                self._log(f"  ! Ошибка: получен невалидный JSON для файла {rel_path}")

        return updated_count

    def _download(self, rel_path: str, url: str):
        """Скачивает и сохраняет один файл."""
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            content = response.text

            target_path = self.prompts_dir.joinpath(rel_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")
        except requests.RequestException as e:
            self._log(f"  ! Не удалось скачать {rel_path} из {url}: {e}")

    def fetch_remote_index(self) -> Dict[str, Dict[str, str]]:
        """Рекурсивно читает дерево каталога с GitHub и возвращает индекс."""
        index: Dict[str, Dict[str, str]] = {}
        stack: List[str] = [GITHUB_API_URL]

        while stack:
            url = stack.pop()
            self._log(f"  > Запрашиваем содержимое API: ...{url[-40:]}")
            response = requests.get(url, timeout=30)
            response.raise_for_status() # Вызовет исключение для кодов 4xx/5xx

            for entry in response.json():
                if not isinstance(entry, dict):
                    self._log(f"  ! Некорректный ответ от GitHub API, пропуск: {entry}")
                    continue

                if entry.get("type") == "dir":
                    stack.append(entry["url"])
                elif entry.get("name", "").endswith(".json"):
                    # Убираем начальный "prompts/" из пути, если он есть
                    path_key = entry["path"]
                    if path_key.startswith("prompts/"):
                        path_key = path_key[len("prompts/"):]

                    index[path_key] = {
                        "sha": entry["sha"],
                        "url": entry["download_url"]
                    }
        return index