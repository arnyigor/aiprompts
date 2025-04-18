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
  Готовые шаблоны для подключения к Python-приложениям
- **🌐 Коллаборация**  
  Улучшение промптов сообществом через Pull Requests

---

## Структура репозитория 📂
*Будет уточняться*
```
├── general/ # Общее / General
├── marketing/ # Маркетинг / Marketing
├── technology/ # Технологии / Technology
├── creative/ # Творчество / Creative
├── business/ # Бизнес / Business
├── education/ # Образование / Education
├── healthcare/ # Здравоохранение / Healthcare
├── legal/ # Юридическое / Legal
├── entertainment/ # Развлечения / Entertainment
├── common_tasks/ # Общие задачи / Common Tasks
├── science/ # Наука / Science
├── model_specific/ # Специфичные модели / Model-Specific
└── environment/ # Окружающая среда / Environment
```

## Категории и теги 🏷️  

*Будут уточняться*

*Теги сформированы из дочерних категорий в структуре.*  
<details>
  <summary>Все возможные категрии и их теги</summary>

### **General / Общее**  
**Теги**:  
`common_tasks`, `education`, `entertainment`, `legal`, `healthcare` 

---

### **Marketing / Маркетинг**  
**Теги**:  
`social_media`, `seo`, `content_marketing`, `advertising`, `branding`  

---

### **Technology / Технологии**  
**Теги**:  
`software`, `data_science`, `ai_ml`, `cloud`, `cybersecurity`, `programming`, `data_analysis`  

---

### **Creative / Творчество**  
**Теги**:  
`design`, `writing`, `art`, `music`, `video`, `game_dev`  

---

### **Business / Бизнес**  
**Теги**:  
`finance`, `hr`, `project_management`, `sales`, `customer_service`  

---

### **Education / Образование**  
**Теги**:  
`courses`, `research`, `language_learning`, `testing`  

---

### **Healthcare / Здравоохранение**  
**Теги**:  
`diagnostics`, `patient_care`, `medical_research`  

---

### **Legal / Юридическое**  
**Теги**:  
`contracts`, `regulations`, `dispute_resolution`  

---

### **Entertainment / Развлечения**  
**Теги**:  
`games`, `music`, `movies`, `books`  

---

### **Social Media / Соцсети**  
**Теги**:  
`instagram`, `facebook`, `tiktok`  

---

### **SEO**  
**Теги**:  
`keyword_optimization`, `content_strategy`  

---

### **AI/ML / ИИ и ML**  
**Теги**:  
`nlp`, `computer_vision`, `reinforcement_learning`  

---

### **Software / Программное обеспечение**  
**Теги**:  
`dev_ops`, `web_dev`, `mobile_dev`  

---

### **Design / Дизайн**  
**Теги**:  
`uiux`, `graphic_design`, `3d_modeling`  

---

### **Writing / Письмо**  
**Теги**:  
`fiction`, `academic`, `technical`  

---

### **Finance / Финансы**  
**Теги**:  
`investment`, `accounting`, `risk_management`  

---

### **HR**  
**Теги**:  
`recruitment`, `training`, `performance`  

---

### **Diagnostics / Диагностика**  
**Теги**:  
`medical_imaging`, `symptom_analysis`  

---

### **Courses / Курсы**  
**Теги**:  
`programming`, `mathematics`, `languages`  

---

### **Games / Игры**  
**Теги**:  
`strategy`, `puzzle`, `casual`  

---

### **Music / Музыка**  
**Теги**:  
`composition`, `production`, `analysis`  

---

### **Common Tasks / Общие задачи**  
**Теги**:  
`productivity`, `translations`, `automation`  

---

### **Science / Наука**  
**Теги**:  
`physics`, `chemistry`, `biology`  

---

### **Model-Specific / Специфичные модели**  
**Теги**:  
`gpt-4`, `dalle`, `stable_diffusion`, `midjourney`  

---

### **Programming / Программирование**  
**Теги**:  
`python`, `javascript`, `data_structures`  

---

### **Data Analysis / Анализ данных**  
**Теги**:  
`statistics`, `big_data`, `visualization`  

---

### **Environment / Окружающая среда**  
**Теги**:  
`climate`, `energy`, `conservation`  

---

### **Game Development / Разработка игр**  
**Теги**:  
`game_design`, `asset_creation`, `level_design`  

</details>

---

### Управление API ключами 🔑
Для использования некоторых функций требуются API ключи:

1. **Добавление ключа**:
   - В редакторе промптов нажмите кнопку ⚙️ рядом с кнопкой Hugging Face
   - В появившемся окне введите ваш API ключ
   - Нажмите "Сохранить"

2. **Безопасность**:
   - Ключи хранятся в зашифрованном виде локально и никуда не передаются
   - Используется алгоритм AES-GCM для шифрования
   - Файлы с ключами имеют ограниченные права доступа

---

## Скриншоты 📸

<details>
  <summary>Скриншоты проекта</summary>

  ![Основное окно](screenshots/main_window.jpg)
_Виджет с поиском, списком промптов и кнопками действий_
  ![Скриншот 1](screenshots/edit_window_1.jpg)
  ![Скриншот 2](screenshots/edit_window_2.jpg)
  ![Скриншот 3](screenshots/edit_window_3.jpg)
  ![Скриншот 4](screenshots/edit_window_4.jpg)
  ![Скриншот 5](screenshots/edit_window_5.jpg)
  ![Скриншот для запросов в Hugging Face](screenshots/hf_window.jpg)

</details>

---

## Как использовать 🛠️
Проект будет использоваться для [aipromptmaster]( https://github.com/arnyigor/aipromptmaster)

---

## Сборка приложения

### Windows
Для сборки приложения используется Auto Py to Exe. Конфигурация сборки находится в файле `auto-py-to-exe-config.json`.

1. Установите зависимости:
```bash
pip install -r requirements.txt
pip install auto-py-to-exe
```

2. MAC Соберите **.app**:
   ```bash
   pyinstaller --onefile --windowed --name "aipromptmaster" src/main.py --distpath .

2. Запустите Auto Py to Exe:
```bash
auto-py-to-exe
```

3. Импортируйте конфигурацию из файла `auto-py-to-exe-config.json`

4. Нажмите кнопку "Convert .py to .exe"

### macOS
1. Установите зависимости:
```bash
pip install -r requirements.txt
pip install pyinstaller
```

2. Соберите приложение:
```bash
pyinstaller --clean --windowed \
            --name "aipromptmaster" \
            --distpath . \
            src/main.py
```

3. Запустите приложение двойным кликом по `aipromptmaster.app`

Примечание: папка `prompts` создастся автоматически при первом запуске приложения.

---

## **Участие в проекте** 🤝
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
