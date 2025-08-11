import logging
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QPushButton, QSpinBox, QDoubleSpinBox, QTextEdit,
                             QMessageBox, QGroupBox, QHBoxLayout)

from hf_model_manager import HFModelManager


class ModelEditorDialog(QDialog):
    """Диалог для редактирования конфигурации модели"""

    def __init__(self, model_manager: HFModelManager, model_name: Optional[str] = None,
                 parent=None):
        super().__init__(parent)
        self.model_manager = model_manager
        self.model_name = model_name
        self.logger = logging.getLogger(__name__)
        self.result = None

        self.setWindowTitle("Редактор модели" if model_name else "Добавление модели")
        self.setup_ui()

        if model_name:
            self.load_model_config()

    def setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout()

        # Основные параметры
        basic_group = QGroupBox("Основные параметры")
        basic_layout = QFormLayout()

        self.name_edit = QLineEdit()
        if self.model_name:
            self.name_edit.setText(self.model_name)
            self.name_edit.setEnabled(False)
        basic_layout.addRow("Имя модели:", self.name_edit)

        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("например: mistralai/Mistral-7B-Instruct-v0.2")
        self.id_edit.setToolTip(
            "Полный путь к модели на Hugging Face.\n"
            "Формат: организация/название-модели\n"
            "Примеры:\n"
            "- mistralai/Mistral-7B-Instruct-v0.2\n"
            "- HuggingFaceH4/zephyr-7b-beta\n"
            "- microsoft/phi-2"
        )
        basic_layout.addRow("Путь к модели:", self.id_edit)

        # Кнопка проверки доступности модели
        self.check_button = QPushButton("Проверить доступность")
        self.check_button.clicked.connect(self.check_model_availability)
        basic_layout.addRow("", self.check_button)

        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        self.description_edit.setPlaceholderText("Опишите особенности и преимущества модели")
        basic_layout.addRow("Описание:", self.description_edit)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Параметры генерации
        params_group = QGroupBox("Параметры генерации")
        params_layout = QFormLayout()

        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(64, 8192)
        self.max_tokens_spin.setValue(4096)
        params_layout.addRow("Макс. токенов:", self.max_tokens_spin)

        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 1.0)
        self.temperature_spin.setSingleStep(0.05)
        self.temperature_spin.setValue(0.7)
        params_layout.addRow("Температура:", self.temperature_spin)

        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setSingleStep(0.05)
        self.top_p_spin.setValue(0.9)
        params_layout.addRow("Top P:", self.top_p_spin)

        self.rep_penalty_spin = QDoubleSpinBox()
        self.rep_penalty_spin.setRange(1.0, 2.0)
        self.rep_penalty_spin.setSingleStep(0.05)
        self.rep_penalty_spin.setValue(1.1)
        params_layout.addRow("Repetition Penalty:", self.rep_penalty_spin)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # Кнопки
        buttons_layout = QHBoxLayout()

        self.save_button = QPushButton("Сохранить")
        self.save_button.clicked.connect(self.save_model)

        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)

        if self.model_name:
            self.delete_button = QPushButton("Удалить")
            self.delete_button.clicked.connect(self.delete_model)
            buttons_layout.addWidget(self.delete_button)

        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def load_model_config(self):
        """Загружает конфигурацию модели в форму"""
        try:
            config = self.model_manager.get_model_config(self.model_name)
            if not config:
                raise ValueError(f"Конфигурация для модели {self.model_name} не найдена")

            self.id_edit.setText(config["id"])
            self.description_edit.setText(config["description"])

            # Используем правильное имя поля - parameters
            params = config.get("parameters") or config.get("params", {})
            self.max_tokens_spin.setValue(params.get("max_new_tokens", 4096))
            self.temperature_spin.setValue(params.get("temperature", 0.7))
            self.top_p_spin.setValue(params.get("top_p", 0.9))
            self.rep_penalty_spin.setValue(params.get("repetition_penalty", 1.1))

        except Exception as e:
            self.logger.error(f"Ошибка при загрузке конфигурации: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить конфигурацию: {str(e)}")

    def get_model_config(self) -> Dict[str, Any]:
        """Собирает конфигурацию модели из формы"""
        return {
            "id": self.id_edit.text().strip(),
            "params": {
                "max_new_tokens": self.max_tokens_spin.value(),
                "temperature": self.temperature_spin.value(),
                "top_p": self.top_p_spin.value(),
                "repetition_penalty": self.rep_penalty_spin.value()
            },
            "description": self.description_edit.toPlainText().strip()
        }

    def check_model_availability(self):
        """Проверяет доступность модели"""
        model_id = self.id_edit.text().strip()
        if not model_id:
            QMessageBox.warning(self, "Ошибка", "Укажите путь к модели")
            return

        try:
            from huggingface_hub import InferenceClient
            client = InferenceClient()
            client.get_model_status(model_id)
            QMessageBox.information(self, "Успех", f"Модель {model_id} доступна")
        except Exception as e:
            error_msg = str(e)
            if "Invalid username or password" in error_msg:
                error_msg = (
                    "Ошибка авторизации в Hugging Face API.\n\n"
                    "Возможные причины:\n"
                    "1. API ключ не указан или указан неверно\n"
                    "2. У вас нет доступа к этой модели\n"
                    "3. Модель недоступна для использования через API\n\n"
                    "Рекомендации:\n"
                    "- Проверьте API ключ в настройках\n"
                    "- Убедитесь, что у вас есть доступ к модели\n"
                    "- Попробуйте использовать другую модель"
                )
            QMessageBox.critical(self, "Ошибка", f"Модель недоступна:\n{error_msg}")

    def validate_form(self) -> bool:
        """Проверяет корректность заполнения формы"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Укажите имя модели")
            return False

        if not self.id_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Укажите путь к модели")
            return False

        if "/" not in self.id_edit.text().strip():
            QMessageBox.warning(
                self,
                "Ошибка",
                "Некорректный путь к модели. Формат: организация/название-модели"
            )
            return False

        if not self.description_edit.toPlainText().strip():
            QMessageBox.warning(self, "Ошибка", "Добавьте описание модели")
            return False

        return True

    def save_model(self):
        """Сохраняет конфигурацию модели"""
        if not self.validate_form():
            return

        try:
            config = self.get_model_config()
            if not self.model_manager.validate_model_config(config):
                raise ValueError("Некорректная конфигурация модели")

            name = self.name_edit.text().strip()
            if self.model_name:  # Обновление существующей модели
                self.model_manager.update_model(
                    name,
                    model_id=config["id"],
                    params=config["params"],
                    description=config["description"]
                )
            else:  # Добавление новой модели
                self.model_manager.add_model(
                    name,
                    config["id"],
                    config["params"],
                    config["description"]
                )

            self.accept()

        except Exception as e:
            self.logger.error(f"Ошибка при сохранении модели: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить модель: {str(e)}")

    def delete_model(self):
        """Удаляет модель"""
        if not self.model_name:
            return

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы уверены, что хотите удалить модель {self.model_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.model_manager.delete_model(self.model_name)
                self.accept()
            except Exception as e:
                self.logger.error(f"Ошибка при удалении модели: {str(e)}")
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить модель: {str(e)}")
