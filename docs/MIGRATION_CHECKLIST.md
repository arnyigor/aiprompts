# Объединение приложений — чек-лист

Состояние: 2026-10-01. Подробности реализации и команды сборки: `G:/Android/AndroidStudioProjects/aipromptmaster/docs/UNIFICATION_STATUS.ru.md`.

- [x] 1. Сохранить исходные репозитории, Git-history и локальные важные файлы; проверить архивы.
- [x] 2. Проверить исходные Android/Desktop сборки и baseline.
- [x] 3. Сравнить Android-копии; сохранить уникальные материалы и основную версию.
- [x] 4. Перенести KMP Desktop в aipromptmaster с Git-history, portable и runtime-проверкой.
- [ ] 5. CI/release.
  - [x] Android/Desktop jobs, проверки common contract, release по точному тегу, локальная проверка YAML.
  - [x] Remote CI Android/Desktop и catalog прошли в draft PR #2 и #29.
  - [ ] Signed release.
- [x] 6. Выделить общий KMP PromptJson, вложенные DTO, storage/manifest и подключить адаптеры обоих клиентов.
- [ ] 7. Миграции и импорт каталога.
  - [x] Mutex, транзакции, legacy upsert, валидированный manifest с checksum, безопасные явные tombstones.
  - [x] Desktop реальные Room migrations 1→3, сохранение private/favorite при tombstones.
  - [x] Android 4→8 ранее проверен на Android 11; последние unit/lint/APK и instrumentation compile прошли.
  - [ ] Проверить Android схемы 1–3: экспортированных схем нет.
  - [ ] Повторить connected instrumentation после текущих изменений: устройство сейчас отсутствует.
- [x] 8. Отделить личные Desktop файлы/JSON-экспорт от каталога, защитить редактирование; добавить явную подготовку кандидатов candidate/stage.
- [x] 9. Schema, validator, воспроизводимый ZIP/manifest/checksums и один catalog publisher; 932 записи проверены.
- [ ] 10. Архивирование legacy.
  - [x] Исходный Desktop, Python и материалы вынесены из рабочего каталога.
  - [x] Полный старый Compose с .git сохранён; оставшиеся 2992 файла сверены SHA-256 с архивом.
  - [ ] Убрать частичный остаток AIPromptMasterCompose после освобождения Windows-папки. Переименование запрещено Windows; удаление отклонено автоматической проверкой без подробного пояснения. Остаток отмечен ARCHIVED.md.
- [x] 11. Удалить проверенные дубли DTO/dependency, лишние kapt/viewBinding и невызываемый GitHub writer; обновить документацию.
- [ ] 12. Финальная проверка.
  - [x] Android unit/contract/lint/APK, Desktop offline regression suite/Room/portable, реальные 932 JSON в обоих roots.
  - [x] Изолированный Desktop runtime: 932 prompts и 932 wire documents, рабочая пользовательская БД не затронута.
  - [x] Подтверждён remote CI; signed publication и installer — отдельные release-проверки.

- [x] Дополнение: перенести улучшение промпта из Python в Desktop (RU/EN, модель, параметры, потоковый предпросмотр, отмена, явное применение к личному черновику). Шесть автономных тестов; исходники Python сохранены.
- [ ] Проверить новое окно визуально и выполнить запрос к выбранному провайдеру. Детали — `aipromptmaster/docs/UNIFICATION_STATUS.ru.md`.

Остаётся два рабочих репозитория: приложения в `aipromptmaster`, публичный каталог в `aiprompts`. UI пока раздельные; Android multi-backstack/свайпы сохранены. Последующее объединение адаптивного UI не входит в этот этап очистки.

Архив: `G:/Android/ProjectArchives/2026-10-01-AiPrompts`. Исходные bundles и ZIP: `C:/Users/ArnyPC/.codex/backups/aiprompts-unification-20260930-215834`.
