# src/sync_manager.py
import hashlib
import json
import os
import requests
from pathlib import Path
from typing import Dict, List

GITHUB_API = (
    "https://api.github.com/repos/arnyigor/aiprompts/contents/prompts"
)  # корень удалённой библиотеки

class SyncManager:
    def __init__(self, prompts_dir: Path, progress_cb=None):
        self.prompts_dir = prompts_dir
        self._progress_cb = progress_cb or (lambda _msg: None)

    # вызываем колбэк при смене фазы
    def _emit(self, msg: str): self._progress_cb(msg)

    def sync(self):
        self._emit("Получаем индекс GitHub…")
        remote = self.fetch_remote_index()

        self._emit("Читаем локальные файлы…")
        local  = self._build_local_index()

        self._emit("Скачиваем новые файлы…")
        self._sync_new_and_deleted(remote, local)

        self._emit("Обновляем изменённые…")
        self._sync_modified(remote, local)

        self._emit("Готово")

    # 2. Индекс локальных файлов (путь -> sha, is_favorite, is_local)
    def _build_local_index(self) -> Dict[str, Dict]:
        index = {}
        for file in self.prompts_dir.rglob("*.json"):
            rel = str(file.relative_to(self.prompts_dir))
            with file.open("rb") as f:
                sha = hashlib.sha1(f.read()).hexdigest()
            data = json.loads(file.read_text(encoding="utf-8"))
            index[rel] = {
                "sha": sha,
                "path": file,
                "is_favorite": data.get("is_favorite", False),
                "is_local": data.get("is_local", False),
            }
        return index

    # 3. Скачиваем новые, удаляем удалённые
    def _sync_new_and_deleted(self, remote, local):
        # новые
        for rel, meta in remote.items():
            if rel not in local:
                self._download(rel, meta["url"])
        # удалённые
        for rel, meta in local.items():
            if rel not in remote and not meta["is_local"]:
                meta["path"].unlink(missing_ok=True)

    # 4. Обновляем изменённые файлы
    def _sync_modified(self, remote, local):
        for rel, l_meta in local.items():
            r_meta = remote.get(rel)
            if not r_meta:                     # файл уже обработан как удалённый
                continue
            if l_meta["sha"] == r_meta["sha"]: # содержимое совпадает
                continue
            # содержимое отличается  → решаем конфликт
            if l_meta["is_local"]:
                continue                       # у пользователя своя версия
            # если в локальном файле только флаг избранного
            fresh = requests.get(r_meta["url"], timeout=20).json()
            fresh["is_favorite"] = l_meta["is_favorite"]  # сохраняем
            (self.prompts_dir / rel).write_text(
                json.dumps(fresh, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    def _download(self, rel_path: str, url: str):
        content = requests.get(url, timeout=20).text
        target  = self.prompts_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def fetch_remote_index(self) -> dict:
        """
        Читает дерево каталога prompts с GitHub и возвращает
        словарь { "relative/path.json": {"sha": "...", "url": "..."} }.
        """
        api_root = ("https://api.github.com/"
                    "repos/arnyigor/aiprompts/contents/prompts")
        index: dict[str, dict] = {}

        stack = [api_root]
        while stack:
            url = stack.pop()
            for entry in requests.get(url, timeout=30).json():
                if entry["type"] == "dir":
                    stack.append(entry["url"])
                elif entry["name"].endswith(".json"):
                    rel = "/".join(entry["path"].split("/")[1:])  # убираем «prompts/»
                    index[rel] = {"sha": entry["sha"],
                                  "url": entry["download_url"]}
        return index
