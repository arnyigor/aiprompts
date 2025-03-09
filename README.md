# 📚 Prompt Library

Репозиторий для централизованного хранения, организации и совместной работы над промптами, используемыми в:
- Чат-ботах
- Генеративных моделях (AI Art, текст)
- NLP-задачах (классификация, анализа тональности)
- Обработке данных

---

## Назначение 🎯
- **🔄 Версионирование**  
  Контроль изменений и история обновлений промптов
- **🗂️ Категоризация**  
  Четкая структура для быстрого поиска
- **🤖 Интеграция**  
  Готовые шаблоны для подключения к Python/JS-приложениям
- **🌐 Коллаборация**  
  Улучшение промптов сообществом через Pull Requests

---

## Структура репозитория 📂
*Будет уточняться*
```
├── text_generation/ # Генерация текстового контента
│ ├── creative_writing/ # Художественные тексты, сценарии
│ │ └── poem_template.md
│ └── technical_docs/ # Документация, технические описания
│ └── api_doc_prompt.json
├── chatbots/ # Диалоговые системы
│ ├── customer_support/ # Шаблоны для поддержки
│ │ ├── faq_prompts/
│ │ └── escalation_template.yaml
│ └── personal_assistant/ # Ассистенты для планирования
├── data_processing/ # Парсинг и трансформация данных
│ ├── csv_formatter.md
│ └── json_extractor.prompt
├── templates/ # Универсальные заготовки
│ ├── base_prompt.mustache
│ └── variables_config.json
└── examples/ # Готовые кейсы
├── marketing/ # Примеры для маркетинга
└── education/ # Обучающие сценарии
```

---

## Скриншоты 📸

### Основное окно приложения
![Основное окно](screenshots/main_window.jpg)
_Виджет с поиском, списком промптов и кнопками действий_

---

## Как использовать 🛠️
Проект будет использоваться для [aipromptmaster]( https://github.com/arnyigor/aipromptmaster)
### Запуск приложения
1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   
2. Запустите через:
   ```bash
   python -m src.main

---

## Сборка исполняемых файлов 🚀
Для создания автономного приложения (Windows: `.exe`, macOS: `.app`) используйте PyInstaller.  
Исполняемый файл должен быть в корне проекта.


### Для Windows:
1. Установите зависимости:
   ```bash
   pip install -r requirements.txt

2. Соберите **.exe**:
   ```bash
   pyinstaller --onefile --windowed --name "aipromptmaster" src/main.py --distpath .
`--name "aipromptmaster"`: Название исполняемого файла.

`--distpath .`: Результат сохраняется в корне проекта.

### Для macOS:
1. Установите зависимости:
   ```bash
   pip install -r requirements.txt

2. Соберите **.app**:
   ```bash
   pyinstaller --onefile --name "aipromptmaster" src/main.py --distpath .

3. Для macOS часто требуется установка **.pyobjc**:
   ```bash
   pip install pyobjc

### Тестирование:
После сборки запустите EXE/APP из корня проекта и проверьте, читаются ли промпты из папки

---

## **Участие в проекте** 🤝
Приветствуются улучшения через:
1. Issues (предложения новых категорий/исправлений)
2. Pull Requests (добавление промптов)
3. Обсуждения в Discussions

---

**Требования к промптам**:
- Четкая структура
- Указание контекста использования
- Теги для поиска (например: #translation #marketing)

Лицензия ⚖️
CC BY-SA 4.0 - Свободное использование с указанием авторства и сохранением лицензии.

## Контакты
Автор: [arnyigor](https://github.com/arnyigor)
Контакты:[Telegram](https://t.me/arnyigor)
Последнее обновление: 09-03-2025
