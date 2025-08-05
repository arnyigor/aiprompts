# importer.py — Конвейер для пакетного импорта промптов из локальных HTML.
# Версия с парсингом структуры <table> и независимым поиском автора/контента.

import argparse
import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup, Tag
from rich.console import Console
from rich.prompt import Prompt


# --- СТРУКТУРЫ ДАННЫХ ---
class AuthorInfo(NamedTuple): id: str; name: str


class AttachmentInfo(NamedTuple): base_name: str; file_type: str; url: str; full_name: str


class ParsedVariant(NamedTuple): name: str; content: str; source: str


class ParsedPost(NamedTuple): title: str; description: str; variants: List[
    ParsedVariant]; author: AuthorInfo; last_edited: Optional[datetime]; tags: List[str]


# --- КЛАСС-ИМПОРТЕР ---
class OfflineImporter:
    def __init__(self, mode: str, config_path: str = "importer_config.json"):
        self.mode = mode;
        self.console = Console();
        script_dir = Path(__file__).parent;
        self.project_root = script_dir.parent
        config_full_path = script_dir / config_path
        try:
            self.config = self._load_config(config_full_path)
        except Exception as e:
            self.console.print(f"[bold red]Критическая ошибка: {e}[/bold red]"); raise SystemExit(1)
        self.input_file = self.project_root / self.config["input_files"][self.mode]
        self.output_dir = self.project_root / self.config["output_dir"]
        self.selectors = self.config["selectors"]
        logging.basicConfig(level=self.config.get("logging_level", "INFO"),
                            format='%(asctime)s - %(levelname)s - %(message)s')

    def _load_config(self, path: Path) -> Dict:
        if not path.is_file(): raise FileNotFoundError(f"Файл конфигурации не найден: {path}")
        config = json.loads(path.read_text(encoding='utf-8'))
        if self.mode not in config.get("input_files", {}): raise ValueError(
            f"В конфиге 'input_files' отсутствует ключ для режима '{self.mode}'")
        if f"{self.mode}_mode" not in config.get("selectors", {}): raise ValueError(
            f"В конфиге 'selectors' отсутствует ключ для режима '{self.mode}_mode'")
        return config

    def run(self):
        self.console.print(
            f"--- Запуск в режиме [bold green]{self.mode}[/bold green], файл: [dim]{self.input_file.name}[/dim] ---")
        if not self.input_file.is_file(): self.console.print(
            f"[bold red]Ошибка: Входной файл не найден: {self.input_file}[/bold red]"); return
        try:
            soup = BeautifulSoup(self.input_file.read_text(encoding='utf-8-sig'), 'lxml')
        except Exception as e:
            logging.error(f"Не удалось прочитать или распарсить HTML-файл {self.input_file}: {e}"); return
        if self.mode == 'index':
            self._process_index_content(soup)
        elif self.mode == 'post':
            self._process_post_content(soup)

    def _process_index_content(self, soup: BeautifulSoup):
        sel = self.selectors['index_mode'];
        container = soup.select_one(sel['container'])
        if not container: logging.warning(f"Не найден контейнер '{sel['container']}' для ссылок."); return
        links = [NamedTuple('PromptLink', url=str, description=str)(url=tag.get('href', ''),
                                                                    description=tag.get_text(strip=True)) for tag in
                 container.select(sel['links'])]
        self.console.print(f"\n[bold green]-- Найдено {len(links)} ссылок на посты --[/bold green]")
        for i, link in enumerate(links, 1): self.console.print(
            f"[cyan]{i}[/cyan]. {link.description} - [dim]{link.url}[/dim]")

    def _process_post_content(self, soup: BeautifulSoup):
        # Аннотация: Теперь ищем главный контейнер (таблицу)
        sel = self.selectors['post_mode']
        post_container_tag = soup.select_one(sel['post_container'])
        if not post_container_tag:
            logging.warning(f"Не найден главный контейнер поста по селектору '{sel['post_container']}'.")
            return
        parsed_data = self._parse_post_heuristically(post_container_tag)
        if parsed_data:
            validated_data = self._interactive_validator(parsed_data)
            if validated_data: self._save_as_json(validated_data)

    def _clean_html_to_text(self, tag: Tag) -> str:
        if not tag: return ""
        for br in tag.find_all("br"): br.replace_with("\n")
        return tag.get_text(separator="\n", strip=True)

    def _process_attachments(self, post_tag: Tag) -> List[ParsedVariant]:
        # ... без изменений ...
        attachment_links = post_tag.select("a.attach-file");
        if not attachment_links: return []
        grouped_attachments: Dict[str, List[AttachmentInfo]] = {}
        for link in attachment_links:
            full_name = link.get_text(strip=True);
            match = re.match(r'^(.*?)\.(txt|pdf|docx)$', full_name, re.IGNORECASE)
            if match: base_name, file_type = match.groups(); info = AttachmentInfo(base_name.strip(), file_type,
                                                                                   link.get('href'),
                                                                                   full_name); grouped_attachments.setdefault(
                base_name, []).append(info)
        variants = []
        for base_name, files in grouped_attachments.items():
            preferred_file = next((f for f in files if f.file_type == 'txt'), None) or next(
                (f for f in files if f.file_type == 'pdf'), files[0])
            self.console.print(f"  -> Обработка вложения: [bold magenta]{preferred_file.full_name}[/bold magenta]")
            if preferred_file.file_type == 'txt':
                try:
                    response = requests.get(preferred_file.url, timeout=10);
                    response.raise_for_status()
                    content = response.content.decode('utf-8', errors='ignore')
                    variants.append(ParsedVariant(name=base_name, content=content, source='file'))
                    self.console.print(f"  [green]✔ Успешно скачано.[/green]")
                except requests.RequestException as e:
                    self.console.print(f"  [red]✖ Ошибка скачивания: {e}[/red]")
            else:
                self.console.print(f"  [yellow]ℹ Пропущено (не .txt).[/yellow]")
        return variants

    def _parse_post_heuristically(self, main_container_tag: Tag) -> Optional[ParsedPost]:
        """Парсер, который теперь работает с главным контейнером поста (таблицей)."""
        sel = self.selectors['post_mode']

        # --- ПОИСК КОНТЕНТА ВНУТРИ КОНТЕЙНЕРА ---
        content_block = main_container_tag.select_one(sel['content_block'])
        if not content_block:
            logging.error(f"Блок контента '{sel['content_block']}' не найден внутри основного контейнера поста.")
            return None

        # --- ДВУХЭТАПНЫЙ ПОИСК АВТОРА ---
        author_info = AuthorInfo(id="", name="Unknown")
        # 1. Основной поиск в главном контейнере (таблице)
        author_span = main_container_tag.select_one('span.normalname > a')
        if author_span:
            name = author_span.get_text(strip=True);
            href = author_span.get('href');
            author_id = ""
            if href:
                try:
                    query_params = parse_qs(urlparse(href).query); author_id = query_params.get('showuser', [""])[0]
                except Exception:
                    pass
            author_info = AuthorInfo(id=author_id, name=name)

        # 2. Запасной поиск в блоке 'edit' (внутри контента)
        last_edited = None
        edit_span = content_block.select_one('span.edit')
        if edit_span:
            if author_info.name == "Unknown":
                editor_tag = edit_span.find('a')
                if editor_tag:
                    # Парсим редактора как запасного автора, если основной не найден
                    editor_name = editor_tag.get_text(strip=True);
                    editor_href = editor_tag.get('href');
                    editor_id = ""
                    if editor_href:
                        try:
                            query_params = parse_qs(urlparse(editor_href).query); editor_id = \
                            query_params.get('showuser', [""])[0]
                        except Exception:
                            pass
                    author_info = AuthorInfo(id=editor_id, name=editor_name)

            date_match = re.search(r'(\d{2}\.\d{2}\.\d{2}, \d{2}:\d{2})', edit_span.get_text())
            last_edited = datetime.strptime(date_match.group(1), '%d.%m.%y, %H:%M') if date_match else None
            edit_span.decompose()

        # --- ВСЯ ДАЛЬНЕЙШАЯ ОБРАБОТКА ИДЕТ С `content_block` ---
        clean_tag = Tag(builder=content_block.builder, name=content_block.name, attrs=content_block.attrs);
        clean_tag.extend(content_block.contents)
        title_match = re.search(r"^(ПРОМПТ\s*\d+)", clean_tag.get_text(strip=True), re.IGNORECASE);
        title = title_match.group(1).strip() if title_match else "Без заголовка"
        description = ""
        first_spoiler = clean_tag.select_one("div.post-block.spoil")
        if first_spoiler:
            intro_nodes = first_spoiler.find_all_previous(string=True);
            full_intro_text = " ".join(node.strip() for node in reversed(intro_nodes)).replace(title, '', 1).strip();
            description = re.sub(r'\s+', ' ', full_intro_text).strip()[:250]
        variants = self._process_attachments(clean_tag)
        if not variants:
            self.console.print("[yellow]Вложения не обработаны. Парсим спойлеры...[/yellow]")
            spoilers = clean_tag.select("div.post-block.spoil .block-body")
            if spoilers:
                variants.append(
                    ParsedVariant(name="Основной", content=self._clean_html_to_text(spoilers[0]), source='spoiler'))
                if len(spoilers) > 1: variants.append(
                    ParsedVariant(name="Пример", content=self._clean_html_to_text(spoilers[1]), source='spoiler'))

        return ParsedPost(title=title, description=description, variants=variants, author=author_info,
                          last_edited=last_edited, tags=[])

    def _interactive_validator(self, data: ParsedPost) -> Optional[ParsedPost]:
        while True:
            self.console.print("\n[bold cyan]-- Обнаружены следующие данные --[/bold cyan]")
            self.console.print(f"[bold]Название:[/bold] {data.title}");
            self.console.print(f"[bold]Описание:[/bold] {data.description or '[пусто]'}")
            self.console.print(f"[bold]Автор:[/bold] {data.author.name} (ID: {data.author.id or 'N/A'})")
            if data.last_edited: self.console.print(
                f"[bold]Дата ред.:[/bold] {data.last_edited.strftime('%Y-%m-%d %H:%M')}")
            self.console.print(f"[bold]Найдено вариантов:[/bold] {len(data.variants)}")
            for i, variant in enumerate(data.variants, 1): self.console.print(
                f"  {i}. [bold magenta]{variant.name}[/bold magenta] (источник: {variant.source}, символов: {len(variant.content)})")
            self.console.print("-" * 30)
            action = Prompt.ask("Ваши действия? [(Y)es/Enter] - сохранить, [(E)dit] - править, [(S)kip] - пропустить",
                                choices=["y", "s", "e"], default="y").lower()
            if action == "y": return data
            if action == "s": self.console.print("[yellow]Пропущено.[/yellow]"); return None
            if action == "e": self.console.print("[yellow]-- Режим редактирования --[/yellow]"); new_title = Prompt.ask(
                "Название", default=data.title); new_desc = Prompt.ask("Описание",
                                                                       default=data.description); data = data._replace(
                title=new_title, description=new_desc)

    def _save_as_json(self, data: ParsedPost):
        now_iso = datetime.now().isoformat();
        prompt_id = str(uuid.uuid4());
        main_content = data.variants[0].content if data.variants else "";
        variants_json = [{"variant_id": {"type": "general", "id": str(i + 1), "priority": i + 1},
                          "content": {"ru": v.content, "en": ""}} for i, v in enumerate(data.variants)]
        json_output = {"id": prompt_id, "title": data.title, "version": "1.0.0", "category": "general",
                       "description": data.description, "content": {"ru": main_content, "en": ""},
                       "prompt_variants": variants_json, "compatible_models": [], "tags": data.tags or ["general"],
                       "variables": [], "status": "active", "is_local": False, "is_favorite": False,
                       "metadata": {"author": {"id": data.author.id, "name": data.author.name}, "source": "4pda.to",
                                    "notes": ""}, "rating": {"score": 0, "votes": 0}, "created_at": now_iso,
                       "updated_at": data.last_edited.isoformat() if data.last_edited else now_iso}
        target_dir = self.output_dir / (json_output["category"]);
        target_dir.mkdir(parents=True, exist_ok=True);
        file_path = target_dir / f"{prompt_id}.json"
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(json_output, f, ensure_ascii=False, indent=2)
            self.console.print(f"[bold green]✔ Успешно сохранено по новой схеме:[/bold green] {file_path}")
        except IOError as e:
            logging.error(f"Не удалось сохранить файл {file_path}: {e}")


# --- ТОЧКА ВХОДА ---
def main():
    parser = argparse.ArgumentParser(description="Офлайн-импортер промптов из HTML.")
    parser.add_argument('--mode', type=str, required=True, choices=['index', 'post'],
                        help="Режим работы: 'index' для списка, 'post' для парсинга поста.")
    args = parser.parse_args()
    try:
        importer = OfflineImporter(mode=args.mode); importer.run()
    except (SystemExit, FileNotFoundError, ValueError) as e:
        if not isinstance(e, SystemExit): print(f"\nОшибка инициализации: {e}")
    except Exception as e:
        logging.critical(f"Произошла непредвиденная ошибка: {e}", exc_info=True)


if __name__ == "__main__":
    main()
