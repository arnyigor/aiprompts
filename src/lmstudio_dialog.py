import logging

# import lmstudio as lms
from PyQt6.QtCore import QTimer, QThreadPool, QRunnable, QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QFormLayout, QLineEdit, QSpinBox,
    QDoubleSpinBox, QPushButton, QTextEdit, QMessageBox, QComboBox, QCheckBox, QLabel
)
# from lmstudio import LlmInstanceInfo, LLM


class AsyncWorker(QRunnable):
    """Асинхронный Worker для выполнения корутин"""

    def __init__(self, parent, handler, logger):
        super().__init__()
        self.parent = parent
        self.handler = handler
        self.logger = logger
        self.signals = WorkerSignals()

        # Подключение сигналов к слотам
        self.signals.update_text.connect(parent.update_output)
        self.signals.enable_apply.connect(parent.apply_button.setEnabled)
        self.signals.show_info.connect(parent.show_message_box)
        self.signals.show_warning.connect(parent.show_message_box)
        self.signals.show_critical.connect(parent.show_message_box)

    def run(self):
        try:
            loop = QThread.currentThread().eventDispatcher().mainLoop()
            loop.callFromThread(self.handler)
        except Exception as e:
            self.logger.error(f"Ошибка в Worker: {str(e)}", exc_info=True)
            self.signals.show_critical.emit("Ошибка", str(e))
        finally:
            self.parent._enable_buttons()


class SyncCheckRunnable(QRunnable):
    def __init__(self, parent, logger):
        super().__init__()
        self.parent = parent
        self.logger = logger
        # Создаем сигналы для обновления UI
        self.signals = WorkerSignals()  # Используем тот же класс сигналов

    def run(self):
        try:
            llm =None # lms.llm()
            response = llm.get_info()  # Синхронный вызов
            if response:
                model_name = response.display_name
                # Отправляем сигналы для обновления
                self.signals.update_text.emit(f"Текущая модель: {model_name}")
                self.signals.show_info.emit("Успех",
                                            f"Соединение с LMStudio установлено\nAPI сервер работает и модель отвечает")
            else:
                self.signals.update_text.emit("Текущая модель: не отвечает")
                self.signals.show_warning.emit("Предупреждение",
                                               "Соединение установлено, но модель не отвечает\nУбедитесь, что модель загружена в LMStudio")
        except Exception as e:
            self.logger.error(f"Ошибка при проверке соединения: {str(e)}", exc_info=True)
            self.signals.show_critical.emit(
                "Ошибка",
                f"Ошибка при проверке соединения: {str(e)}\n"
                "Убедитесь что:\n"
                "1. LMStudio запущен\n"
                "2. Модель загружена\n"
                "3. API сервер активен (зеленый индикатор)\n"
                "4. Порт 1234 доступен\n"
                "5. URL API указан верно"
            )


class WorkerSignals(QObject):
    """Сигналы для Worker"""
    update_text = pyqtSignal(str)
    enable_apply = pyqtSignal(bool)
    show_info = pyqtSignal(str, str)
    show_warning = pyqtSignal(str, str)
    show_critical = pyqtSignal(str, str)
    finished = pyqtSignal()  # Сигнал завершения работы


class Worker(QRunnable):
    """Класс для выполнения задач в отдельном потоке"""

    def __init__(self, parent, handler, logger):
        super().__init__()
        self.parent = parent
        self.handler = handler
        self.logger = logger
        self.signals = WorkerSignals()

        # Подключаем сигналы к слотам
        self.signals.update_text.connect(parent.update_output)
        self.signals.enable_apply.connect(lambda enabled: parent.apply_button.setEnabled(enabled))
        self.signals.show_info.connect(parent.show_message_box)
        self.signals.show_warning.connect(parent.show_message_box)
        self.signals.show_critical.connect(parent.show_message_box)
        self.signals.finished.connect(parent._enable_buttons)

    def run(self):
        try:
            self.logger.debug("Worker начал выполнение")
            self.handler()
        except Exception as e:
            self.logger.error(f"Ошибка в Worker: {str(e)}", exc_info=True)
            self.signals.show_critical.emit("Ошибка", str(e))
        finally:
            self.signals.finished.emit()


class LMStudioDialog(QDialog):
    def __init__(self, prompt_text="", parent=None, from_preview=False):
        super().__init__(parent)
        self.response = None
        self.logger = logging.getLogger(__name__)
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
        self.improve_mode.setChecked(
            not from_preview)  # Включен по умолчанию только если не из preview
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

    async def check_connection_async(self) -> None:
        """
        Асинхронная проверка соединения с моделью.
        :return: True, если соединение успешно; иначе False.
        """
        try:
            llm = None # lms.llm()
            self.response = await llm.get_info()
            if self.response:
                model_name = self.response.display_name
                self.model_info.setText(f"Текущая модель: {model_name}")
                QMessageBox.information(
                    self, "Успех",
                    f"Соединение с LMStudio установлено\nAPI сервер работает и модель отвечает"
                )
            else:
                self.model_info.setText("Текущая модель: не отвечает")
                QMessageBox.warning(
                    self, "Предупреждение",
                    "Соединение установлено, но модель не отвечает\nУбедитесь, что модель загружена в LMStudio"
                )
        except Exception as e:
            self.logger.error(f"Ошибка при проверке соединения: {str(e)}", exc_info=True,
                              stack_info=True)
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка при проверке соединения: {str(e)}\n"
                "Убедитесь что:\n"
                "1. LMStudio запущен\n"
                "2. Модель загружена\n"
                "3. API сервер активен (зеленый индикатор)\n"
                "4. Порт 1234 доступен\n"
                "5. URL API указан верно"
            )

    def check_connection(self):
        worker = SyncCheckRunnable(self, self.logger)
        # Подключаем сигналы к слотам
        worker.signals.update_text.connect(self.model_info.setText)
        worker.signals.show_info.connect(self.show_message_box)
        worker.signals.show_warning.connect(self.show_message_box)
        worker.signals.show_critical.connect(self.show_message_box)
        QThreadPool.globalInstance().start(worker)

    def show_message_box(self, level, title, message):
        if level == "info":
            QMessageBox.information(self, title, message)
        elif level == "warning":
            QMessageBox.warning(self, title, message)
        elif level == "critical":
            QMessageBox.critical(self, title, message)

    def update_output(self, text):
        """Обновляет поле вывода с автоматической прокруткой вниз"""
        try:
            # Обновляем текст
            self.output_field.setPlainText(text)
            
            # Прокручиваем до конца
            scrollbar = self.output_field.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
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
        QTimer.singleShot(0, lambda: self.run_button.setEnabled(True))
        QTimer.singleShot(0, lambda: self.run_button.setText("Выполнить"))
        QTimer.singleShot(0, lambda: self.close_button.setEnabled(True))

    def _process_request(self, prompt_text: str):
        """Обработка запроса к модели через LMStudio API"""
        try:
            self.logger.debug("Начало обработки запроса")

            # Создаем чат и добавляем сообщения
            chat = None # lms.Chat()
            
            # Добавляем системный промпт, если есть
            system_prompt = self.system_prompt.toPlainText().strip()
            if system_prompt:
                chat.add_system_message(system_prompt)
                
            # Добавляем сообщение пользователя
            chat.add_user_message(prompt_text)

            # Подготовка параметров запроса
            config = {
                "temperature": self.temperature.value(),
                "maxTokens": self.max_tokens.value(),
                "format": self.chat_format.currentText().lower()
            }

            # Получаем модель
            try:
                model = None # lms.llm()
                model_info = model.get_info()
                self.logger.debug(f"Отправка запроса к LMStudio с моделью {model_info.display_name}")
            except Exception as e:
                raise RuntimeError(f"Ошибка при получении модели: {str(e)}")
            
            # Выполняем запрос через LMStudio API
            full_response = []
            is_truncated = False

            try:
                # Получаем потоковый ответ
                prediction_stream = model.respond_stream(
                    chat,
                    config=config,
                    on_message=chat.append  # Автоматически добавляем ответы в историю чата
                )

                for fragment in prediction_stream:
                    if not fragment or not fragment.content:
                        continue
                        
                    content = fragment.content
                    # Проверка на токены завершения
                    if any(token in content for token in ["</s>", "<|im_end|>", "<|endoftext|>"]):
                        is_truncated = True
                        content = content.replace("</s>", "").replace("<|im_end|>", "").replace("<|endoftext|>", "")

                    full_response.append(content)
                    # Частичное обновление UI каждые 5 чанков
                    if len(full_response) % 5 == 0:
                        current_text = "".join(full_response)
                        self.current_worker.signals.update_text.emit(current_text)
                        QThread.msleep(10)  # Небольшая задержка для обработки событий UI

                # Получаем статистику генерации
                result = prediction_stream.result()
                self.logger.debug(f"Сгенерировано токенов: {result.stats.predicted_tokens_count}")
                self.logger.debug(f"Время до первого токена: {result.stats.time_to_first_token_sec} сек")
                self.logger.debug(f"Причина остановки: {result.stats.stop_reason}")

            except Exception as e:
                raise RuntimeError(f"Ошибка при генерации ответа: {str(e)}")

            # Формирование итогового результата
            final_text = "".join(full_response).strip()
            if final_text:
                if is_truncated:
                    final_text += "\n\n[Внимание: ответ был обрезан. Увеличьте лимит токенов]"
                    self.logger.warning("Обнаружен обрезанный ответ")

                self.result = final_text
                self.current_worker.signals.update_text.emit(final_text)
                self.current_worker.signals.enable_apply.emit(True)
            else:
                raise RuntimeError("Пустой ответ от модели")

        except Exception as e:
            error_msg = f"Ошибка обработки запроса: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.current_worker.signals.show_critical.emit("Ошибка", error_msg)
            self.current_worker.signals.update_text.emit(error_msg)

        finally:
            self.current_worker.signals.finished.emit()

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
