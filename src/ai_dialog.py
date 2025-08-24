# ai_dialog.py
import logging
import re
import time
from typing import Dict

from PyQt6.QtCore import QThreadPool, QRunnable, pyqtSignal, QObject
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QFormLayout, QLineEdit, QSpinBox,
    QDoubleSpinBox, QPushButton, QTextEdit, QMessageBox, QComboBox, QCheckBox, QLabel,
    QProgressBar, QWidget
)

# Используем ваш рабочий блок импортов
try:
    from src.llm_client import LLMClient
    from src.adapter import AdapterLLMClient
    from src.client_factory import LLMClientFactory
    from src.interfaces import LLMConnectionError

    YOUR_CLIENT_AVAILABLE = True
except ImportError as e:
    LLMClient, AdapterLLMClient, LLMClientFactory, LLMConnectionError = None, None, None, Exception
    YOUR_CLIENT_AVAILABLE = False
    IMPORT_ERROR_MESSAGE = f"Не удалось импортировать модули LLM-клиента:\n{e}"
    logging.error("Ошибка импорта в ai_dialog", exc_info=True)


class AccordionWidget(QWidget):
    """Виджет-аккордеон для отображения сворачиваемого контента"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.is_expanded = False
        self.setup_ui(title)

    def setup_ui(self, title):
        layout = QVBoxLayout(self);
        layout.setContentsMargins(0, 0, 0, 0);
        layout.setSpacing(0)
        self.header = QPushButton(title);
        self.header.setCheckable(True);
        self.header.setChecked(False)
        self.header.setStyleSheet("""
            QPushButton { text-align: left; font-weight: bold; background-color: #e0e0e0; border: 1px solid #cccccc; padding: 8px; border-radius: 4px; }
            QPushButton:checked { background-color: #d0d0d0; } QPushButton:hover { background-color: #d8d8d8; }
        """)
        self.header.clicked.connect(self.toggle_content)
        self.content_widget = QWidget();
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10);
        self.content_widget.setVisible(False)
        self.content_widget.setStyleSheet(
            "QWidget { background-color: #f8f9fa; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 4px 4px; }")
        layout.addWidget(self.header);
        layout.addWidget(self.content_widget)

    def toggle_content(self):
        self.is_expanded = not self.is_expanded;
        self.content_widget.setVisible(self.is_expanded);
        self.header.setChecked(self.is_expanded)

    def set_content_widget(self, widget: QWidget):
        for i in reversed(range(self.content_layout.count())): self.content_layout.itemAt(i).widget().setParent(None)
        self.content_layout.addWidget(widget)

    def set_expanded(self, expanded: bool):
        if self.is_expanded != expanded:
            self.is_expanded = expanded;
            self.content_widget.setVisible(expanded);
            self.header.setChecked(expanded)


class WorkerSignals(QObject):
    """Сигналы для безопасного обновления UI из фоновых потоков."""
    update_output = pyqtSignal(str)
    update_thinking = pyqtSignal(str)
    clear_all = pyqtSignal()
    enable_apply = pyqtSignal(bool)
    show_warning = pyqtSignal(str, str)
    show_info = pyqtSignal(str, str)
    show_critical = pyqtSignal(str, str)
    finished = pyqtSignal()
    check_finished = pyqtSignal()
    update_text = pyqtSignal(str)
    update_final_metrics = pyqtSignal(dict)
    # --- НОВЫЕ СИГНАЛЫ ДЛЯ РЕАЛЬНОГО ВРЕМЕНИ ---
    update_ttft = pyqtSignal(float)
    update_generation_metrics = pyqtSignal(int, float)


class CheckConnectionRunnable(QRunnable):
    """Простой и надежный QRunnable для проверки соединения."""

    def __init__(self, parent_dialog, logger):
        super().__init__();
        self.parent = parent_dialog;
        self.logger = logger;
        self.signals = WorkerSignals()

    def run(self):
        try:
            if not YOUR_CLIENT_AVAILABLE: self.signals.show_critical.emit("Ошибка", IMPORT_ERROR_MESSAGE); return
            model_config = self.parent.get_current_model_config()
            LLMClientFactory.create_provider(model_config)
            self.signals.update_text.emit(f"Сервер '{model_config['client_type']}' доступен")
            self.signals.show_info.emit("Успех", "Соединение с API-сервером успешно установлено.")
        except (LLMConnectionError, ValueError) as e:
            self.logger.warning(f"Ошибка при проверке соединения: {str(e)}")
            self.signals.update_text.emit("Статус: ошибка соединения");
            self.signals.show_critical.emit("Ошибка соединения", str(e))
        except Exception as e:
            self.logger.critical("Неперехваченное исключение!", exc_info=True);
            self.signals.show_critical.emit("Критическая ошибка", str(e))
        finally:
            self.signals.check_finished.emit()


class RequestWorker(QRunnable):
    """QRunnable для выполнения запроса с замерами статистики на клиенте."""

    def __init__(self, parent_dialog, model_config: dict, prompt_text: str, logger):
        super().__init__()
        self.parent = parent_dialog;
        self.model_config = model_config;
        self.prompt_text = prompt_text;
        self.logger = logger
        self.signals = WorkerSignals();
        self._is_cancelled = False;
        self.is_thinking = False;
        self.buffer = ""

    def cancel(self):
        self._is_cancelled = True

    def _parse_think_response(self, text: str) -> Dict[str, str]:
        think_pattern = r'<think>(.*?)</think>'
        match = re.search(think_pattern, text, re.DOTALL)
        thinking = match.group(1).strip() if match else ""
        cleaned = re.sub(think_pattern, '', text, flags=re.DOTALL).strip()
        return {"thinking_response": thinking, "llm_response": cleaned}

    # В файле ai_dialog.py, класс RequestWorker

    def run(self):
        try:
            if self._is_cancelled: return

            self.signals.clear_all.emit()

            prompt_tokens = round(len(self.prompt_text) / 4)
            self.signals.update_generation_metrics.emit(0, 0.0)
            self.parent.tokens_prompt_label.setText(str(prompt_tokens))

            provider = LLMClientFactory.create_provider(self.model_config)
            llm_client = LLMClient(provider, self.model_config)
            messages = [{"role": "user", "content": self.prompt_text}]
            use_stream = self.model_config.get("inference", {}).get("stream", True)

            start_time = time.perf_counter()

            if use_stream:
                response_or_stream = llm_client.chat(messages, stream=use_stream)
                full_response_text = "" # Будем собирать полный текст для кнопки "Применить"

                is_first_chunk = True
                first_chunk_time = 0
                total_tokens = 0

                for chunk in response_or_stream:
                    if self._is_cancelled: break

                    if is_first_chunk:
                        first_chunk_time = time.perf_counter()
                        ttft_ms = (first_chunk_time - start_time) * 1000
                        self.signals.update_ttft.emit(ttft_ms)
                        is_first_chunk = False

                    delta = provider.extract_delta_from_chunk(chunk)
                    if not delta: continue
                    if isinstance(delta, dict): delta = delta.get("content", "")
                    if not isinstance(delta, str): continue

                    total_tokens += (len(delta) / 4)
                    elapsed_generation_time = time.perf_counter() - first_chunk_time
                    speed = total_tokens / elapsed_generation_time if elapsed_generation_time > 0 else 0
                    self.signals.update_generation_metrics.emit(round(total_tokens), speed)

                    self.buffer += delta

                    while True:
                        if self.is_thinking:
                            end_tag_pos = self.buffer.find('</think>')
                            if end_tag_pos != -1:
                                self.signals.update_thinking.emit(self.buffer[:end_tag_pos])
                                self.buffer = self.buffer[end_tag_pos + len('</think>'):]
                                self.is_thinking = False
                            else:
                                self.signals.update_thinking.emit(self.buffer)
                                break
                        else: # Если не в режиме "мышления"
                            start_tag_pos = self.buffer.find('<think>')
                            if start_tag_pos != -1:
                                # Нашли тег. Стримим всё, что было до него, в основной результат.
                                part_to_stream = self.buffer[:start_tag_pos]
                                self.signals.update_output.emit(part_to_stream)
                                full_response_text += part_to_stream

                                self.buffer = self.buffer[start_tag_pos + len('<think>'):]
                                self.is_thinking = True
                            else:
                                # Тега нет. Стримим весь буфер в основной результат.
                                self.signals.update_output.emit(self.buffer)
                                full_response_text += self.buffer
                                self.buffer = ""
                                break

                if not self._is_cancelled:
                    # Добавляем остаток из буфера, если он есть
                    if self.buffer and not self.is_thinking:
                        self.signals.update_output.emit(self.buffer)
                        full_response_text += self.buffer

                    # Сохраняем итоговый результат
                    final_text = full_response_text.strip()
                    if final_text:
                        self.parent.result = final_text
                        self.signals.enable_apply.emit(True)
            else:
                response_dict = llm_client.chat(messages, stream=False)
                metadata = provider.extract_metadata_from_response(response_dict)
                if metadata: self.signals.update_final_metrics.emit(metadata)
                choices = provider.extract_choices(response_dict)
                final_response_str = provider.extract_content_from_choice(choices[0]) if choices else ""
                parsed = self._parse_think_response(final_response_str)
                if parsed["thinking_response"]: self.signals.update_thinking.emit(parsed["thinking_response"])
                text = parsed["llm_response"]
                self.signals.update_output.emit(text)
                if text: self.parent.result = text; self.signals.enable_apply.emit(True)

        except Exception as e:
            if not self._is_cancelled:
                self.logger.critical("Неперехваченное исключение!", exc_info=True)
                self.signals.update_output.emit(f"\n\n--- ОШИБКА ---\n{e}")
        finally:
            self.signals.finished.emit()


class AIDialog(QDialog):
    def __init__(self, prompt_text="", parent=None, from_preview=False):
        super().__init__(parent);
        self.logger = logging.getLogger(__name__);
        self.result = None;
        self.active_worker = None
        self.setWindowTitle("Запрос к LLM");
        self.setGeometry(200, 200, 800, 750)
        if not YOUR_CLIENT_AVAILABLE: self._setup_unavailable_ui(); return
        self._setup_main_ui(prompt_text, from_preview)

    def _setup_unavailable_ui(self):
        layout = QVBoxLayout(self);
        error_label = QLabel(IMPORT_ERROR_MESSAGE)
        error_label.setStyleSheet("font-size: 14px; color: red;");
        error_label.setWordWrap(True)
        layout.addWidget(error_label);
        close_btn = QPushButton("Закрыть");
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)

    def _setup_main_ui(self, prompt_text, from_preview):
        layout = QVBoxLayout(self)
        # --- API Group ---
        api_group = QGroupBox("Настройки соединения");
        api_layout = QFormLayout(api_group)
        self.provider_selector = QComboBox();
        self.providers = {
            "LM Studio": {"type": "lmstudio", "url": "http://127.0.0.1:1234/v1"},
            "Ollama": {"type": "ollama", "url": "http://localhost:11434"},
            "Jan": {"type": "jan", "url": "http://127.0.0.1:1337/v1"},
            "Другой (OpenAI-совм.)": {"type": "openai_compatible", "url": ""},
        }
        self.provider_selector.addItems(self.providers.keys());
        self.provider_selector.currentTextChanged.connect(self.on_provider_changed)
        self.api_url = QLineEdit();
        self.model_name_field = QLineEdit();
        self.model_name_field.setPlaceholderText("(необязательно)")
        api_layout.addRow("Провайдер:", self.provider_selector);
        api_layout.addRow("URL API:", self.api_url);
        api_layout.addRow("Имя модели:", self.model_name_field)
        self.model_info = QLabel("Статус: не определен");
        api_layout.addRow(self.model_info)
        self.check_connection_btn = QPushButton("Проверить соединение");
        self.check_connection_btn.clicked.connect(self.check_connection)
        api_layout.addRow(self.check_connection_btn);
        self.on_provider_changed(self.provider_selector.currentText())
        # --- Params Group ---
        params_group = QGroupBox("Параметры");
        params_layout = QFormLayout(params_group)
        self.improve_mode = QCheckBox("Улучшить промпт перед отправкой");
        self.improve_mode.setChecked(not from_preview);
        params_layout.addRow(self.improve_mode)
        self.temperature = QDoubleSpinBox();
        self.temperature.setRange(0.0, 2.0);
        self.temperature.setSingleStep(0.1);
        self.temperature.setValue(0.7);
        params_layout.addRow("Температура:", self.temperature)
        self.max_tokens = QSpinBox();
        self.max_tokens.setRange(-1, 16384);
        self.max_tokens.setValue(1024);
        self.max_tokens.setToolTip("-1 для безлимита");
        params_layout.addRow("Макс. токенов:", self.max_tokens)
        self.stream_checkbox = QCheckBox("Потоковый ответ (stream)");
        self.stream_checkbox.setChecked(True);
        params_layout.addRow(self.stream_checkbox)
        # --- Prompt Group ---
        prompt_group = QGroupBox("Промпт");
        prompt_layout = QVBoxLayout(prompt_group)
        self.prompt_field = QTextEdit(prompt_text);
        prompt_layout.addWidget(self.prompt_field)
        # --- Run Widget ---
        run_widget = QWidget();
        run_layout = QHBoxLayout(run_widget);
        run_layout.setContentsMargins(0, 0, 0, 0)
        self.run_button = QPushButton("Выполнить");
        self.run_button.clicked.connect(self.execute_prompt)
        self.cancel_button = QPushButton("Отмена");
        self.cancel_button.clicked.connect(self.cancel_request);
        self.cancel_button.setVisible(False)
        self.progress_bar = QProgressBar();
        self.progress_bar.setRange(0, 0);
        self.progress_bar.setVisible(False)
        run_layout.addWidget(self.run_button);
        run_layout.addWidget(self.cancel_button);
        run_layout.addWidget(self.progress_bar)
        # --- Thinking Accordion ---
        self.thinking_accordion = AccordionWidget("🧠 Мысли модели (Chain-of-Thought)");
        self.thinking_output = QTextEdit();
        self.thinking_output.setReadOnly(True)
        self.thinking_accordion.set_content_widget(self.thinking_output)
        # --- Output Group ---
        output_group = QGroupBox("Результат");
        output_layout = QVBoxLayout(output_group)
        self.output_field = QTextEdit();
        self.output_field.setReadOnly(True);
        output_layout.addWidget(self.output_field)
        # --- Metrics Group ---
        self.metrics_group = QGroupBox("📊 Статистика ответа");
        metrics_layout = QFormLayout(self.metrics_group)
        self.ttft_label = QLabel("0.0 мс");
        self.speed_label = QLabel("0.0 токен/сек")
        self.tokens_prompt_label = QLabel("0");
        self.tokens_eval_label = QLabel("0")
        metrics_layout.addRow("Время до первого токена (TTFT):", self.ttft_label);
        metrics_layout.addRow("Скорость генерации:", self.speed_label)
        metrics_layout.addRow("Токены (промпт):", self.tokens_prompt_label);
        metrics_layout.addRow("Токены (ответ):", self.tokens_eval_label)
        self.metrics_group.setVisible(False)
        # --- Bottom Buttons ---
        button_layout = QHBoxLayout();
        self.apply_button = QPushButton("Вернуть результат");
        self.apply_button.clicked.connect(self.apply_result);
        self.apply_button.setEnabled(False)
        self.close_button = QPushButton("Закрыть");
        self.close_button.clicked.connect(self.reject)
        button_layout.addStretch();
        button_layout.addWidget(self.apply_button);
        button_layout.addWidget(self.close_button)
        # --- Final Layout Assembly ---
        layout.addWidget(api_group);
        layout.addWidget(params_group);
        layout.addWidget(prompt_group)
        layout.addWidget(run_widget);
        layout.addWidget(self.thinking_accordion);
        layout.addWidget(output_group)
        layout.addWidget(self.metrics_group);
        layout.addLayout(button_layout)

    def on_provider_changed(self, provider_name: str):
        config = self.providers.get(provider_name);
        if config: self.api_url.setText(config["url"])

    def get_current_model_config(self) -> dict:
        p_name = self.provider_selector.currentText();
        p_type = self.providers.get(p_name, {}).get("type", "openai_compatible")
        return {"name": self.model_name_field.text().strip() or "default-model", "client_type": p_type,
                "api_base": self.api_url.text().strip(), "inference": {"stream": self.stream_checkbox.isChecked()},
                "generation": {"max_tokens": self.max_tokens.value(), "temperature": self.temperature.value()}}

    def check_connection(self):
        self.check_connection_btn.setEnabled(False);
        self.check_connection_btn.setText("Проверка...")
        worker = CheckConnectionRunnable(self, self.logger)
        worker.signals.check_finished.connect(self.on_check_connection_finished);
        worker.signals.update_text.connect(self.model_info.setText)
        worker.signals.show_info.connect(self.show_message_box);
        worker.signals.show_critical.connect(self.show_message_box)
        QThreadPool.globalInstance().start(worker)

    def on_check_connection_finished(self):
        self.check_connection_btn.setEnabled(True);
        self.check_connection_btn.setText("Проверить соединение")

    def show_message_box(self, title, message):
        if title.lower() == "успех":
            QMessageBox.information(self, title, message)
        elif title.lower() == "предупреждение":
            QMessageBox.warning(self, title, message)
        else:
            QMessageBox.critical(self, title, message)

    def update_output(self, text: str):
        self.output_field.insertPlainText(text)
        self.output_field.moveCursor(QTextCursor.MoveOperation.End)

    def update_thinking_output(self, text: str):
        if text.strip() and not self.thinking_accordion.is_expanded: self.thinking_accordion.set_expanded(True)
        self.thinking_output.setPlainText(text);
        self.thinking_output.moveCursor(QTextCursor.MoveOperation.End)

    def clear_outputs(self):
        self.output_field.clear();
        self.thinking_output.clear();
        self.thinking_accordion.set_expanded(False)
        self.metrics_group.setVisible(True);
        self.ttft_label.setText("0.0 мс");
        self.speed_label.setText("0.0 токен/сек")
        self.tokens_prompt_label.setText("0");
        self.tokens_eval_label.setText("0")

    # --- МЕТОДЫ ДЛЯ ОБНОВЛЕНИЯ СТАТИСТИКИ ---
    def update_ttft_display(self, ttft_ms: float):
        self.ttft_label.setText(f"{ttft_ms:.2f} мс")

    def update_generation_display(self, tokens: int, speed: float):
        self.tokens_eval_label.setText(str(tokens))
        self.speed_label.setText(f"{speed:.2f} токен/сек")

    def update_final_metrics_display(self, metrics: dict):
        if not metrics: return
        prompt_tokens = metrics.get('prompt_eval_count', 0);
        eval_tokens = metrics.get('eval_count', 0)
        ttft_ns = metrics.get('prompt_eval_duration', 0);
        eval_ns = metrics.get('eval_duration', 0)
        ttft_ms = round(ttft_ns / 1_000_000, 2);
        eval_s = eval_ns / 1_000_000_000
        speed = round(eval_tokens / eval_s, 2) if eval_s > 0 else 0
        self.ttft_label.setText(f"{ttft_ms} мс");
        self.speed_label.setText(f"{speed} токен/сек")
        self.tokens_prompt_label.setText(str(prompt_tokens));
        self.tokens_eval_label.setText(str(eval_tokens))

    # ----------------------------------------

    def execute_prompt(self):
        prompt_text = self.prompt_field.toPlainText().strip()
        if not prompt_text: self.show_message_box("Предупреждение", "Промпт не может быть пустым."); return
        self._set_ui_for_request(True)
        final_prompt = f"Улучши следующий промпт...\n\n{prompt_text}" if self.improve_mode.isChecked() else prompt_text

        self.active_worker = RequestWorker(self, self.get_current_model_config(), final_prompt, self.logger)
        self.active_worker.signals.finished.connect(self._on_request_finished)
        self.active_worker.signals.clear_all.connect(self.clear_outputs)
        self.active_worker.signals.update_output.connect(self.update_output)
        self.active_worker.signals.update_thinking.connect(self.update_thinking_output)
        self.active_worker.signals.update_final_metrics.connect(self.update_final_metrics_display)
        self.active_worker.signals.update_ttft.connect(self.update_ttft_display)
        self.active_worker.signals.update_generation_metrics.connect(self.update_generation_display)
        self.active_worker.signals.enable_apply.connect(self.apply_button.setEnabled)
        self.active_worker.signals.show_warning.connect(self.show_message_box)
        QThreadPool.globalInstance().start(self.active_worker)

    def _on_request_finished(self):
        self._set_ui_for_request(False);
        self.active_worker = None

    def _set_ui_for_request(self, is_running: bool):
        self.run_button.setVisible(not is_running);
        self.cancel_button.setVisible(is_running)
        self.progress_bar.setVisible(is_running)
        self.apply_button.setEnabled(not is_running and self.result is not None)
        self.close_button.setEnabled(not is_running)
        if is_running: self.metrics_group.setVisible(True)

    def cancel_request(self):
        if self.active_worker: self.active_worker.cancel(); self.logger.info("Запрос отменен пользователем")

    def apply_result(self):
        if self.result:
            self.accept()
        else:
            self.show_message_box("Предупреждение", "Нет результата для возврата.")

    def get_result(self):
        return self.result

    def closeEvent(self, event):
        if self.active_worker: self.active_worker.cancel()
        QThreadPool.globalInstance().waitForDone(1000)
        super().closeEvent(event)
