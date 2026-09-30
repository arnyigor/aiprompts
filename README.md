# aiprompts — публичный каталог

Приложения Android и Desktop находятся в репозитории `arnyigor/aipromptmaster`. Этот репозиторий хранит публичные промпты, схему, инструменты проверки и один publisher. Основная ветка — `master`.

## Структура

- `prompts/<category>/<id>.json` — опубликованные промпты.
- `catalog/prompt.schema.json` — формат записи; дополнительные поля сохраняются.
- `catalog/deleted-ids.json` — явно рассмотренные удаления публичных ID; сейчас пусто.
- `scripts/catalog.py` — validate, stage, candidate, package.
- `.github/workflows/catalog.yml` — проверка PR и публикация проверенного ZIP из master.
- `docs/MIGRATION_CHECKLIST.md` — состояние миграции приложений и архивов.

## Проверка и упаковка

```powershell
python -m pip install -r catalog/requirements.txt
python scripts/catalog.py validate
python -m unittest discover -s scripts -p 'test_*.py'
python scripts/catalog.py package
```

Результат в `dist`: `prompts.zip`, `catalog-manifest.json`, `checksums.sha256`. ZIP содержит все записи и `catalog.manifest`; расширение manifest совместимо со старыми клиентами, которые читают только JSON. Manifest содержит версии, источник Git, ID, пути и SHA-256 каждого файла. Одинаковый исходный каталог и commit дают одинаковый ZIP. Локальный package отражает рабочие файлы; publisher работает только с checkout указанного commit.

## Добавление и редактирование

Desktop сохраняет личные промпты в `%USERPROFILE%/.aiprompts/personal_prompts`, а личный JSON-экспорт — в общем формате с пользовательскими флагами и заметками. Из личного экспорта явно подготовьте один публичный кандидат:

```powershell
python scripts/catalog.py candidate --source personal-export.json --id PROMPT_ID --output review
```

Для отдельного JSON `--id` не нужен. Команда снимает личные флаги и удаляет metadata.notes, сохраняет исходный файл, варианты и переменные. Просмотрите текст, автора и source перед публикацией: сам текст может содержать личные сведения. Уже публичную запись можно перенести в review командой `stage --source prompt.json --output review`; личные файлы эта команда отклоняет.

Проверьте `python scripts/catalog.py validate --prompts review`, затем внесите рассмотренную запись в `prompts/<category>/<id>.json` и оформите обычный Git diff/PR. Не переименовывайте ID при правке: это идентичность записи. Смена категории означает перенос существующего ID; заголовки могут совпадать. Команды stage/candidate не перезаписывают существующий файл.

При намеренном удалении удалите JSON и добавьте его ID в `catalog/deleted-ids.json` в том же PR. Новые клиенты применяют только явные tombstones из полностью проверенного ZIP; личные записи, избранное и записи с заметками сохраняются. Старый ZIP без manifest не даёт права удалять отсутствующие ID.

## Публикация

После merge в master единственный workflow проверяет каталог и обновляет `latest-prompts`. PR только проверяется; публикация с рабочей ветки запрещена. Старые APK/Python releases, второй publisher, webhook sync и PR notifier отключены и сохранены в `docs/legacy-workflows`.

Исторические приложения и локальные файлы находятся в `G:/Android/ProjectArchives/2026-10-01-AiPrompts`. Исходные Git bundles и ZIP — в `C:/Users/ArnyPC/.codex/backups/aiprompts-unification-20260930-215834`. Это локальные архивы, не публичные файлы каталога.
