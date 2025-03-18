import logging

from PyQt6.QtCore import QTimer, QThreadPool, QRunnable, QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QFormLayout, QLineEdit, QSpinBox,
    QDoubleSpinBox, QPushButton, QTextEdit, QMessageBox, QComboBox, QCheckBox, QLabel
)


class WorkerSignals(QObject):
    """Сигналы для Worker"""
    update_text = pyqtSignal(str)
    enable_apply = pyqtSignal()


class Worker(QRunnable):
    """Класс для выполнения задач в отдельном потоке"""

    def __init__(self, parent, handler, logger):
        super().__init__()
        self.parent = parent
        self.handler = handler
        self.logger = logger
        self.signals = WorkerSignals()
        # Подключаем сигналы к слотам
        self.signals.update_text.connect(self.parent.output_field.setPlainText)
        self.signals.enable_apply.connect(lambda: self.parent.apply_button.setEnabled(True))

    def run(self):
        try:
            self.logger.debug("Worker начал выполнение")
            self.handler()
        except Exception as e:
            self.logger.error(f"Ошибка в Worker: {str(e)}", exc_info=True)
        finally:
            QTimer.singleShot(0, lambda: self.parent.run_button.setEnabled(True))
            QTimer.singleShot(0, lambda: self.parent.run_button.setText("Выполнить"))


class LMStudioDialog(QDialog):
    def __init__(self, lm_api, prompt_text="", parent=None, from_preview=False):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.lm_api = lm_api
        self.result = None
        self.current_worker = None

        # Настройка окна
        self.setWindowTitle("Запрос к LMStudio")
        self.setGeometry(200, 200, 800, 600)

        # Создаем layout
        layout = QVBoxLayout()

        # Группа настроек API
        api_group = QGroupBox("Настройки LMStudio")
        api_layout = QFormLayout()

        self.api_url = QLineEdit("http://localhost:1234/v1")
        api_layout.addRow("URL API:", self.api_url)

        # Информация о текущей модели
        self.model_info = QLabel("Текущая модель: не определена")
        self.model_info.setWordWrap(True)
        api_layout.addRow(self.model_info)

        # Кнопка проверки соединения
        self.check_connection_btn = QPushButton("Проверить соединение")
        self.check_connection_btn.clicked.connect(self.check_connection)
        api_layout.addRow(self.check_connection_btn)

        api_group.setLayout(api_layout)
        layout.addWidget(api_group)

        # Группа параметров запроса
        params_group = QGroupBox("Параметры запроса")
        params_layout = QFormLayout()

        # Переключатель режима улучшения промптов
        self.improve_mode = QCheckBox("Режим улучшения промптов")
        self.improve_mode.setChecked(not from_preview)  # Включен по умолчанию только если не из preview
        self.improve_mode.setToolTip(
            "Включите для автоматического улучшения структуры и качества промпта")
        params_layout.addRow(self.improve_mode)

        # Системный промпт
        self.system_prompt = QTextEdit()
        self.system_prompt.setPlaceholderText("Введите системный промпт (необязательно)...")
        self.system_prompt.setMaximumHeight(100)
        params_layout.addRow("Системный промпт:", self.system_prompt)

        # Формат чата
        self.chat_format = QComboBox()
        self.chat_format.addItems([
            "ChatML",
            "Alpaca",
            "Vicuna",
            "OpenAI",
            "Llama2",
            "Mistral"
        ])
        params_layout.addRow("Формат чата:", self.chat_format)

        # Базовые параметры генерации
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0.0, 2.0)
        self.temperature.setSingleStep(0.1)
        self.temperature.setValue(0.7)
        params_layout.addRow("Температура:", self.temperature)

        self.max_tokens = QSpinBox()
        self.max_tokens.setRange(64, 4096)
        self.max_tokens.setValue(256)
        params_layout.addRow("Макс. токенов:", self.max_tokens)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # Поле ввода промпта
        prompt_group = QGroupBox("Промпт")
        prompt_layout = QVBoxLayout()
        self.prompt_field = QTextEdit()
        self.prompt_field.setPlainText(prompt_text)
        self.prompt_field.setMinimumHeight(100)
        prompt_layout.addWidget(self.prompt_field)
        prompt_group.setLayout(prompt_layout)
        layout.addWidget(prompt_group)

        # Кнопка выполнения
        self.run_button = QPushButton("Выполнить")
        self.run_button.clicked.connect(self.execute_prompt)
        layout.addWidget(self.run_button)

        # Поле вывода
        output_group = QGroupBox("Результат")
        output_layout = QVBoxLayout()
        self.output_field = QTextEdit()
        self.output_field.setReadOnly(True)
        self.output_field.setMinimumHeight(150)
        output_layout.addWidget(self.output_field)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        # Кнопки управления
        button_layout = QHBoxLayout()
        self.apply_button = QPushButton("Вернуть результат в редактор")
        self.apply_button.clicked.connect(self.apply_result)
        self.apply_button.setEnabled(False)

        self.close_button = QPushButton("Закрыть без сохранения")
        self.close_button.clicked.connect(self.reject)

        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def check_connection(self):
        """Проверяет соединение с LMStudio API"""
        try:
            self.lm_api.base_url = self.api_url.text()

            # Отправляем тестовый запрос к API
            test_messages = [{"role": "user", "content": "test"}]
            test_params = {
                "temperature": 0.7,
                "max_new_tokens": 1,
                "chat_format": "chatml",
                "stream": False
            }

            # Пробуем получить ответ от модели через существующий метод
            try:
                # Используем генератор для получения одного ответа
                response_gen = self.lm_api.query_model(test_messages, **test_params)
                response = next(response_gen, None)

                if response:
                    # Получаем имя модели из логов или используем значение по умолчанию
                    model_name = "Модель активна"
                    self.model_info.setText(f"Текущая модель: {model_name}")
                    QMessageBox.information(self, "Успех",
                                            f"Соединение с LMStudio установлено\n"
                                            f"API сервер работает и модель отвечает")
                else:
                    self.model_info.setText("Текущая модель: не отвечает")
                    QMessageBox.warning(self, "Предупреждение",
                                        "Соединение установлено, но модель не отвечает\n"
                                        "Убедитесь, что модель загружена в LMStudio")
            except StopIteration:
                # Если генератор пустой, но ошибки нет - соединение есть
                self.model_info.setText("Текущая модель: загружается")
                QMessageBox.information(self, "Успех",
                                        "Соединение с LMStudio установлено\n"
                                        "Модель может быть в процессе загрузки")

        except Exception as e:
            self.logger.error(f"Ошибка подключения к LMStudio: {str(e)}", exc_info=True)
            self.model_info.setText("Текущая модель: ошибка подключения")
            QMessageBox.critical(self, "Ошибка",
                                 f"Ошибка при проверке соединения: {str(e)}\n\n"
                                 "Убедитесь что:\n"
                                 "1. LMStudio запущен\n"
                                 "2. Модель загружена\n"
                                 "3. API сервер активен (зеленый индикатор)\n"
                                 "4. Порт 1234 доступен\n"
                                 "5. URL API указан верно")

    def update_output(self, text):
        """Обновляет поле вывода"""
        try:
            if self.current_worker:
                self.current_worker.signals.update_text.emit(str(text))
            else:
                self.logger.warning("current_worker не установлен")

        except Exception as e:
            self.logger.error(f"Ошибка при обновлении вывода: {str(e)}", exc_info=True)

    def execute_prompt(self):
        """Отправляет запрос к модели"""
        prompt_text = self.prompt_field.toPlainText()

        if not prompt_text:
            QMessageBox.warning(self, "Предупреждение", "Введите текст промпта")
            return

        # Блокируем кнопки
        self.run_button.setEnabled(False)
        self.run_button.setText("Выполняется...")
        self.apply_button.setEnabled(False)
        self.close_button.setEnabled(False)

        if self.improve_mode.isChecked():
            # Добавляем инструкции для улучшения промпта
            enhanced_prompt = (
                "Ты - опытный эксперт по промпт-инжинирингу. Твоя задача - улучшить следующий промпт, "
                "сделав его более эффективным и структурированным.\n\n"
                "ИСХОДНЫЙ ПРОМПТ:\n"
                f"{prompt_text}\n\n"
                "ИНСТРУКЦИИ ПО УЛУЧШЕНИЮ:\n"
                "1. Определи роль и цель: Четко укажи, какую роль должен играть ИИ и какой результат ожидается\n"
                "2. Добавь контекст: Предоставь необходимую предысторию и условия\n"
                "3. Уточни требования: Укажи конкретные параметры, ограничения и критерии качества\n"
                "4. Структурируй информацию: Используй четкие разделы и маркеры\n"
                "5. Задай формат ответа: Опиши желаемую структуру и стиль ответа\n"
                "6. Добавь примеры: Если уместно, включи образцы желаемого результата\n\n"
                "ФОРМАТ УЛУЧШЕННОГО ПРОМПТА:\n\n"
                "### Роль и контекст\n"
                "[Определи роль ИИ и общий контекст задачи]\n\n"
                "### Основная задача\n"
                "[Четко опиши, что нужно сделать]\n\n"
                "### Требования и ограничения\n"
                "[Укажи обязательные параметры и ограничения]\n\n"
                "### Формат ответа\n"
                "[Опиши структуру и стиль ожидаемого ответа]\n\n"
                "### Дополнительные указания\n"
                "[Добавь примеры или уточнения при необходимости]\n\n"
                "ВАЖНО:\n"
                "- Сохрани основную цель и смысл исходного промпта\n"
                "- Используй четкий и профессиональный язык\n"
                "- Добавь конкретные метрики успеха\n"
                "- Учитывай возможные ограничения модели\n\n"
                "Пожалуйста, верни только улучшенную версию промпта, следуя указанному формату, "
                "без дополнительных пояснений или комментариев."
            )
        else:
            enhanced_prompt = prompt_text

        # Создаем и запускаем worker
        try:
            # Обновляем URL API перед запуском
            self.lm_api.base_url = self.api_url.text()

            worker = Worker(
                parent=self,
                handler=lambda: self._process_request(enhanced_prompt),
                logger=self.logger
            )
            self.current_worker = worker
            QThreadPool.globalInstance().start(worker)

        except Exception as e:
            self.logger.error(f"Ошибка при запуске worker: {str(e)}", exc_info=True)
            self.update_output(f"Ошибка при запуске обработчика: {str(e)}")
            self._enable_buttons()

    def _enable_buttons(self):
        """Включает все кнопки"""
        self.run_button.setEnabled(True)
        self.run_button.setText("Выполнить")
        self.close_button.setEnabled(True)

    def _process_request(self, prompt_text: str):
        """Обработка запроса к модели"""
        try:
            self.logger.debug("Начало обработки запроса")

            messages = []

            # Добавляем системный промпт, если он указан
            system_prompt = self.system_prompt.toPlainText().strip()
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": prompt_text})

            params = {
                "temperature": self.temperature.value(),
                "max_new_tokens": self.max_tokens.value(),
                "chat_format": self.chat_format.currentText().lower(),
                "stop": None  # Отключаем принудительную остановку
            }

            self.logger.debug("Получение ответа от модели...")
            response_generator = self.lm_api.query_model(messages, **params)

            full_response = ""
            chunk_counter = 0
            update_frequency = 5  # Обновляем каждые N чанков
            is_truncated = False  # Флаг обрезания ответа

            try:
                for chunk in response_generator:
                    if chunk:
                        # Проверяем на специальные токены завершения
                        if "<|endoftext|>" in chunk or "</s>" in chunk:
                            is_truncated = True
                            chunk = chunk.replace("<|endoftext|>", "").replace("</s>", "")

                        full_response += chunk
                        chunk_counter += 1

                        # Обновляем UI каждые update_frequency чанков
                        if chunk_counter % update_frequency == 0:
                            self.update_output(full_response)
                            QThread.msleep(10)  # Небольшая задержка для обработки UI

                # Финальное обновление UI
                if full_response:
                    self.logger.debug(f"Получен полный ответ длиной {len(full_response)} символов")
                    self.result = full_response.strip()

                    # Добавляем предупреждение, если ответ был обрезан
                    if is_truncated:
                        self.logger.warning("Ответ был обрезан")
                        self.result += "\n\n[Внимание: ответ был обрезан. Попробуйте увеличить максимальное количество токенов]"

                    self.update_output(self.result)

                    if self.current_worker:
                        self.current_worker.signals.enable_apply.emit()
                else:
                    error_msg = "Не удалось получить ответ от модели"
                    self.logger.error(error_msg)
                    self.update_output(error_msg)

            except Exception as e:
                self.logger.error(f"Ошибка при получении частей ответа: {str(e)}", exc_info=True)
                raise

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Ошибка в обработке запроса: {error_msg}", exc_info=True)
            self.update_output(f"Произошла ошибка: {error_msg}")

        finally:
            self._enable_buttons()

    def apply_result(self):
        """Возвращает результат в редактор промптов"""
        if self.result:
            self.accept()
        else:
            self.logger.warning("Попытка применить пустой результат")
            QMessageBox.warning(self, "Предупреждение",
                                "Нет результата для возврата. Сначала выполните запрос.")

    def get_result(self):
        """Возвращает результат только если диалог был принят"""
        return self.result
