import logging

from PyQt6.QtCore import QMetaObject, Q_ARG
from PyQt6.QtCore import Qt, QTimer, QThreadPool, QRunnable
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QComboBox, QDialog, QGroupBox, QFormLayout, QSlider, QSpinBox, QLabel, \
    QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout, QMessageBox


class Worker(QRunnable):
    """Класс для выполнения задач в отдельном потоке"""

    def __init__(self, parent, handler, logger):
        super().__init__()
        self.parent = parent
        self.handler = handler
        self.logger = logger

    def run(self):
        try:
            self.logger.debug("Worker начал выполнение")
            self.handler()
        except Exception as e:
            self.logger.error(f"Ошибка в Worker: {str(e)}", exc_info=True)
        finally:
            # Обновляем состояние кнопки через главный поток
            QTimer.singleShot(0, lambda: self.parent.run_button.setEnabled(True))
            QTimer.singleShot(0, lambda: self.parent.run_button.setText("Выполнить"))


class HuggingFaceDialog(QDialog):
    MODELS = {
        "Mistral-7B-Instruct": {
            "id": "mistralai/Mistral-7B-Instruct-v0.2",
            "params": {
                "max_new_tokens": 256,
                "temperature": 0.7,
                "top_p": 0.85,
                "repetition_penalty": 1.1,
            },
            "description": "Мощная модель с хорошим балансом качества и производительности. Отлично подходит для русского языка."
        },
        "Zephyr-7B": {
            "id": "HuggingFaceH4/zephyr-7b-beta",
            "params": {
                "max_new_tokens": 200,
                "temperature": 0.7,
                "top_p": 0.9,
                "repetition_penalty": 1.15,
            },
            "description": "Специализированная модель для инструкций и промптов. Хорошо следует указаниям."
        },
        "SOLAR-10.7B-Instruct": {
            "id": "upstage/SOLAR-10.7B-Instruct-v1.0",
            "params": {
                "max_new_tokens": 150,
                "temperature": 0.65,
                "top_p": 0.9,
                "repetition_penalty": 1.2,
            },
            "description": "Продвинутая модель с отличным пониманием контекста и генерацией текста."
        },
        "Phi-2": {
            "id": "microsoft/phi-2",
            "params": {
                "max_new_tokens": 180,
                "temperature": 0.75,
                "top_p": 0.9,
                "repetition_penalty": 1.1,
            },
            "description": "Компактная но мощная модель от Microsoft. Хорошо работает с техническими текстами."
        },
        "Starling-LM": {
            "id": "berkeley-nest/Starling-LM-7B-alpha",
            "params": {
                "max_new_tokens": 200,
                "temperature": 0.7,
                "top_p": 0.85,
                "repetition_penalty": 1.15,
            },
            "description": "Оптимизирована для следования инструкциям и генерации качественных ответов."
        },
        "Gemma-3-12B-Instruct": {
            "id": "google/gemma-3-4b-pt",
            "params": {
                "max_new_tokens": 256,  # Максимальное количество новых токенов
                "temperature": 0.6,
                # Температура генерации (более низкое значение для детерминированности)
                "top_p": 0.9,  # Вероятностное обрезание для Nucleus Sampling
                "repetition_penalty": 1.2,  # Штраф за повторение фраз
            },
            # Описание модели
            "description": (
                    "Мультимодальная модель от Google с поддержкой текста и изображений, "
                    + f"128K контекстным окном и мультиязычной поддержкой (140+ языков). "
                    + f"Подходит для задач анализа изображений, генерации текста и ответов на вопросы."
            )
        }
    }

    def __init__(self, hf_api, prompt_text="", parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.hf_api = hf_api
        self.result = None

        # Настройка окна
        self.setWindowTitle("Запрос к Hugging Face API")
        self.setGeometry(200, 200, 800, 600)

        # Выбор модели
        self.model_selector = QComboBox()
        for model_name in self.MODELS.keys():
            self.model_selector.addItem(model_name)

        # Настройки модели
        self.settings_group = QGroupBox("Настройки модели")
        settings_layout = QFormLayout()

        # Исправляем создание слайдера
        self.temperature_slider = QSlider(Qt.Orientation.Horizontal)  # Исправленная строка
        self.temperature_slider.setRange(0, 100)
        self.temperature_slider.setValue(70)
        self.temperature_label = QLabel("0.7")
        self.temperature_slider.valueChanged.connect(
            lambda v: self.temperature_label.setText(f"{v / 100:.1f}")
        )

        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(64, 4096)
        self.max_tokens_spin.setValue(1024)

        settings_layout.addRow("Температура:", self.temperature_slider)
        settings_layout.addRow("Значение:", self.temperature_label)
        settings_layout.addRow("Макс. токенов:", self.max_tokens_spin)
        self.settings_group.setLayout(settings_layout)

        # Остальные элементы интерфейса
        self.prompt_field = QTextEdit()
        self.prompt_field.setPlainText(prompt_text)
        self.prompt_field.setMinimumHeight(200)

        self.run_button = QPushButton("Выполнить")
        self.run_button.clicked.connect(self.execute_prompt)

        self.output_field = QTextEdit()
        self.output_field.setReadOnly(True)
        self.output_field.setMinimumHeight(200)

        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.accept)

        self.apply_button = QPushButton("Вернуть результат в редактор")
        self.apply_button.clicked.connect(self.apply_result)
        self.apply_button.setEnabled(False)  # Изначально кнопка неактивна

        self.close_button = QPushButton("Закрыть без сохранения")
        self.close_button.clicked.connect(self.reject)  # Используем reject вместо accept

        self.model_description = QLabel()
        self.model_description.setWordWrap(True)
        self.model_selector.currentTextChanged.connect(self.update_model_description)

        # Компоновка
        layout = QVBoxLayout()
        # Обновляем layout
        layout.addWidget(QLabel("Выберите модель:"))
        layout.addWidget(self.model_selector)
        layout.addWidget(self.model_description)
        layout.addWidget(self.settings_group)
        layout.addWidget(QLabel("Промпт:"))
        layout.addWidget(self.prompt_field)
        layout.addWidget(self.run_button)
        layout.addWidget(QLabel("Результат:"))
        layout.addWidget(self.output_field)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)

        # Устанавливаем начальное описание
        self.update_model_description(self.model_selector.currentText())
        self.setLayout(layout)

    def update_model_description(self, model_name: str):
        """Обновляет описание выбранной модели"""
        description = self.MODELS[model_name]["description"]
        self.model_description.setText(f"Описание: {description}")

        # Обновляем параметры по умолчанию
        params = self.MODELS[model_name]["params"]
        self.temperature_slider.setValue(int(params["temperature"] * 100))
        self.max_tokens_spin.setValue(params["max_new_tokens"])

    def apply_result(self):
        """Возвращает результат в редактор промптов"""
        if self.result:
            self.accept()  # Используем accept для подтверждения результата
        else:
            self.logger.warning("Попытка применить пустой результат")
            QMessageBox.warning(self, "Предупреждение",
                                "Нет результата для возврата. Сначала выполните запрос.")

    def get_result(self):
        """Возвращает результат только если диалог был принят"""
        if self.result is None:
            self.logger.warning("Попытка получить пустой результат")
        return self.result

    def update_output(self, text):
        """Обновляет поле вывода"""
        try:
            # Устанавливаем текст
            QMetaObject.invokeMethod(
                self.output_field,
                "setPlainText",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, str(text))
            )

            # Прокрутка к концу текста
            QMetaObject.invokeMethod(
                self.output_field,
                "moveCursor",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(int, QTextCursor.MoveOperation.End)
            )

        except Exception as e:
            self.logger.error(f"Ошибка при обновлении вывода: {str(e)}", exc_info=True)

    def execute_prompt(self):
        """Отправляет запрос к выбранной модели"""
        model_name = self.model_selector.currentText()
        model_config = self.MODELS[model_name]

        # Получаем текст промпта
        prompt_text = self.prompt_field.toPlainText()

        # Добавляем инструкции для улучшения промпта
        enhanced_prompt = (
            "Ты - опытный эксперт по промпт-инжинирингу. Твоя задача - улучшить следующий промпт, "
            "используя лучшие практики:\n\n"
            "ИСХОДНЫЙ ПРОМПТ:\n"
            f"{prompt_text}\n\n"
            "ИНСТРУКЦИИ ПО УЛУЧШЕНИЮ:\n"
            "1. Сделай промпт более конкретным и четким\n"
            "2. Добавь контекст и ограничения\n"
            "3. Структурируй информацию в логическом порядке\n"
            "4. Используй маркеры для разделения частей промпта\n"
            "5. Укажи желаемый формат ответа\n"
            "6. Добавь примеры, если это уместно\n\n"
            "ФОРМАТ ОТВЕТА:\n"
            "### Роль и контекст\n"
            "[Определи роль ИИ и контекст задачи]\n\n"
            "### Основная задача\n"
            "[Четко сформулируй, что нужно сделать]\n\n"
            "### Ограничения и требования\n"
            "[Укажи важные ограничения и специальные требования]\n\n"
            "### Формат вывода\n"
            "[Опиши, как должен быть структурирован ответ]\n\n"
            "### Дополнительные указания\n"
            "[Добавь уточнения или примеры при необходимости]\n\n"
            "ВАЖНО:\n"
            "- Сохрани исходную цель и основной смысл промпта\n"
            "- Используй профессиональный, но понятный язык\n"
            "- Добавь конкретные метрики или критерии успеха\n"
            "- Учитывай возможные ограничения модели\n\n"
            "Пожалуйста, верни только улучшенную версию промпта, следуя указанному формату, "
            "без дополнительных пояснений или комментариев."
        )

        # Проверяем длину текста
        if len(enhanced_prompt) > 1000:  # Уменьшаем максимальную длину
            warning_msg = "Текст слишком длинный. Он будет обрезан до 1000 символов."
            self.logger.warning(warning_msg)
            QMessageBox.warning(self, "Предупреждение", warning_msg)
            enhanced_prompt = enhanced_prompt[:1000]

        # Обновляем параметры
        params = model_config["params"].copy()
        params.update({
            "temperature": self.temperature_slider.value() / 100,
            "max_new_tokens": self.max_tokens_spin.value(),
            "do_sample": True,
            "return_full_text": False,
            "truncation": True,
        })

        # Отключаем кнопку и меняем текст
        self.run_button.setEnabled(False)
        self.run_button.setText("Выполняется...")

        try:
            # Создаем и запускаем worker
            worker = Worker(
                parent=self,
                handler=lambda: self._process_request(enhanced_prompt, params, model_config["id"]),
                logger=self.logger
            )
            QThreadPool.globalInstance().start(worker)

        except Exception as e:
            self.logger.error(f"Ошибка при запуске worker: {str(e)}", exc_info=True)
            self.update_output(f"Ошибка при запуске обработчика: {str(e)}")
            self.run_button.setEnabled(True)
            self.run_button.setText("Выполнить")

    def _process_request(self, prompt_text: str, params: dict, model_id: str):
        """Обработка запроса к модели"""
        try:
            self.logger.debug("Начало обработки запроса")
            self.update_output("Отправка запроса к модели...")

            messages = [{"role": "user", "content": prompt_text}]

            # Убираем неподдерживаемые параметры
            allowed_params = {
                'max_new_tokens', 'temperature', 'top_p',
                'repetition_penalty', 'do_sample', 'return_full_text'
            }
            filtered_params = {k: v for k, v in params.items() if k in allowed_params}

            # Устанавливаем выбранную модель и параметры
            self.hf_api.model_name = model_id
            response = self.hf_api.query_model(
                messages,
                **filtered_params
            )

            self.logger.debug(f"Получен ответ: {response[:100]}...")

            if response and isinstance(response, str):
                # Очищаем возможные специальные токены из ответа
                cleaned_response = (response
                                    .replace("<|Assistant|>:", "")
                                    .replace("<|User|>:", "")
                                    .strip())
                self.update_output(cleaned_response)
                self.result = cleaned_response
                # Активируем кнопку в главном потоке
                QMetaObject.invokeMethod(
                    self.apply_button,
                    "setEnabled",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(bool, True)
                )
            else:
                error_msg = "Не удалось получить ответ от модели"
                self.logger.error(error_msg)
                self.update_output(error_msg)
                self.show_error_message(error_msg)

        except Exception as e:
            error_msg = str(e)
            if "out of memory" in error_msg.lower():
                error_msg = ("Недостаточно памяти. Попробуйте:\n"
                             "1. Уменьшить длину входного текста\n"
                             "2. Выбрать модель с меткой (Low Memory)\n"
                             "3. Уменьшить максимальное количество токенов")

            self.logger.error(f"Ошибка в обработке запроса: {error_msg}", exc_info=True)
            self.update_output(f"Произошла ошибка: {error_msg}")
            self.show_error_message(error_msg)

    def show_error_message(self, message: str):
        """Показывает сообщение об ошибке в главном потоке"""
        try:
            from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(
                self,
                "_show_error_dialog",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, message)
            )
        except Exception as e:
            self.logger.error(f"Ошибка при показе сообщения об ошибке: {str(e)}", exc_info=True)
