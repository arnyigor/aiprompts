import logging

from PyQt6.QtCore import QTimer, QThreadPool, QRunnable, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QFormLayout, QLineEdit, QSpinBox,
    QDoubleSpinBox, QPushButton, QTextEdit, QMessageBox, QComboBox, QApplication
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
    def __init__(self, lm_api, prompt_text="", parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.lm_api = lm_api
        self.result = None
        self.current_worker = None  # Сохраняем ссылку на текущий worker

        # Настройка окна
        self.setWindowTitle("Запрос к LMStudio")
        self.setGeometry(200, 200, 800, 600)

        # Создаем layout
        layout = QVBoxLayout()

        # Группа настроек API
        api_group = QGroupBox("Настройки API")
        api_layout = QFormLayout()

        self.api_url = QLineEdit("http://localhost:1234/v1")
        api_layout.addRow("URL API:", self.api_url)

        # Кнопка проверки соединения
        self.check_connection_btn = QPushButton("Проверить соединение")
        self.check_connection_btn.clicked.connect(self.check_connection)
        api_layout.addRow(self.check_connection_btn)

        api_group.setLayout(api_layout)
        layout.addWidget(api_group)

        # Группа параметров модели
        params_group = QGroupBox("Параметры генерации")
        params_layout = QFormLayout()

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

        self.max_tokens = QSpinBox()
        self.max_tokens.setRange(64, 8192)
        self.max_tokens.setValue(2048)
        params_layout.addRow("Макс. токенов:", self.max_tokens)

        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0.1, 2.0)
        self.temperature.setValue(0.7)
        self.temperature.setSingleStep(0.1)
        params_layout.addRow("Температура:", self.temperature)

        self.top_p = QDoubleSpinBox()
        self.top_p.setRange(0.1, 1.0)
        self.top_p.setValue(0.95)
        self.top_p.setSingleStep(0.05)
        params_layout.addRow("Top P:", self.top_p)

        # Дополнительные параметры
        self.repeat_penalty = QDoubleSpinBox()
        self.repeat_penalty.setRange(1.0, 2.0)
        self.repeat_penalty.setValue(1.1)
        self.repeat_penalty.setSingleStep(0.1)
        params_layout.addRow("Штраф за повторы:", self.repeat_penalty)

        self.presence_penalty = QDoubleSpinBox()
        self.presence_penalty.setRange(-2.0, 2.0)
        self.presence_penalty.setValue(0.0)
        self.presence_penalty.setSingleStep(0.1)
        params_layout.addRow("Штраф за присутствие:", self.presence_penalty)

        self.frequency_penalty = QDoubleSpinBox()
        self.frequency_penalty.setRange(-2.0, 2.0)
        self.frequency_penalty.setValue(0.0)
        self.frequency_penalty.setSingleStep(0.1)
        params_layout.addRow("Штраф за частоту:", self.frequency_penalty)

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

        # Кнопки действий
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
            if self.lm_api.check_connection():
                QMessageBox.information(self, "Успех", "Соединение с LMStudio установлено")
            else:
                QMessageBox.warning(self, "Ошибка",
                                    "Не удалось подключиться к LMStudio.\n"
                                    "Убедитесь, что приложение запущено и API доступен.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при проверке соединения: {str(e)}")

    def update_output(self, text):
        """Обновляет поле вывода"""
        try:
            # self.logger.debug(f"update_output вызван с текстом длиной {len(str(text))} символов")
            # self.logger.debug(f"Текущий поток: {'главный' if QThread.currentThread() is QApplication.instance().thread() else 'фоновый'}")
            
            if self.current_worker:
                self.current_worker.signals.update_text.emit(str(text))
                self.logger.debug("Отправлен сигнал обновления текста")
            else:
                self.logger.warning("current_worker не установлен")
                
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении вывода: {str(e)}", exc_info=True)

    def execute_prompt(self):
        """Отправляет запрос к модели"""
        prompt_text = self.prompt_field.toPlainText()
        if not prompt_text.strip():
            QMessageBox.warning(self, "Предупреждение", "Введите промпт")
            return

        # Отключаем кнопку и меняем текст
        self.run_button.setEnabled(False)
        self.run_button.setText("Выполняется...")

        try:
            # Обновляем URL API
            self.lm_api.base_url = self.api_url.text()

            # Создаем и запускаем worker
            self.current_worker = Worker(
                parent=self,
                handler=lambda: self._process_request(prompt_text),
                logger=self.logger
            )
            QThreadPool.globalInstance().start(self.current_worker)

        except Exception as e:
            self.logger.error(f"Ошибка при запуске worker: {str(e)}", exc_info=True)
            self.update_output(f"Ошибка при запуске обработчика: {str(e)}")
            self.run_button.setEnabled(True)
            self.run_button.setText("Выполнить")

    def _process_request(self, prompt_text: str):
        """Обработка запроса к модели"""
        try:
            self.logger.debug("Начало обработки запроса")
            self.logger.debug(f"Текущий поток: {'главный' if QThread.currentThread() is QApplication.instance().thread() else 'фоновый'}")
            
            # Блокируем кнопки через сигналы
            QTimer.singleShot(0, lambda: self.run_button.setEnabled(False))
            QTimer.singleShot(0, lambda: self.apply_button.setEnabled(False))
            QTimer.singleShot(0, lambda: self.close_button.setEnabled(False))
            self.logger.debug("Кнопки заблокированы")
            
            messages = []
            
            # Добавляем системный промпт, если он указан
            system_prompt = self.system_prompt.toPlainText().strip()
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
                
            messages.append({"role": "user", "content": prompt_text})
            
            params = {
                "temperature": self.temperature.value(),
                "max_new_tokens": self.max_tokens.value(),
                "top_p": self.top_p.value(),
                "repeat_penalty": self.repeat_penalty.value(),
                "presence_penalty": self.presence_penalty.value(),
                "frequency_penalty": self.frequency_penalty.value(),
                "chat_format": self.chat_format.currentText().lower()
            }
            
            self.logger.debug("Получение ответа от модели...")
            # Получаем генератор ответов
            response_generator = self.lm_api.query_model(messages, **params)
            
            # Собираем полный ответ из частей
            full_response = ""
            chunks_processed = 0
            try:
                for chunk in response_generator:
                    if chunk:  # Проверяем, что chunk не пустой
                        chunks_processed += 1
                        full_response += chunk
                        # self.logger.debug(f"Обработан чанк {chunks_processed}, длина ответа: {len(full_response)}")
                        # Обновляем текст через сигнал
                        self.update_output(full_response)
                        QThread.msleep(10)  # Небольшая задержка для обработки UI
            except Exception as e:
                self.logger.error(f"Ошибка при получении частей ответа: {str(e)}", exc_info=True)
                raise
                
            self.logger.debug(f"Обработка завершена. Всего обработано чанков: {chunks_processed}")
            self.logger.debug(f"Итоговая длина ответа: {len(full_response)}")
            
            if full_response:
                self.logger.debug("Сохранение результата и активация кнопки применения")
                self.result = full_response
                if self.current_worker:
                    self.current_worker.signals.enable_apply.emit()
            else:
                error_msg = "Не удалось получить ответ от модели"
                self.logger.error(error_msg)
                self.update_output(error_msg)
                
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Ошибка в обработке запроса: {error_msg}", exc_info=True)
            self.update_output(f"Произошла ошибка: {error_msg}")
            
        finally:
            self.logger.debug("Восстановление состояния кнопок")
            # Восстанавливаем состояние кнопок через сигналы
            QTimer.singleShot(0, lambda: self.run_button.setEnabled(True))
            QTimer.singleShot(0, lambda: self.close_button.setEnabled(True))
            QTimer.singleShot(0, lambda: self.run_button.setText("Выполнить"))

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
