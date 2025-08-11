import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit,
    QMessageBox, QGroupBox
)

from llm_settings import Settings


class ApiKeysDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.settings = settings

        self.setWindowTitle("Управление API ключами")
        self.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Hugging Face
        hf_group = QGroupBox("Hugging Face")
        hf_layout = QVBoxLayout()

        # Текущий статус
        hf_status_layout = QHBoxLayout()
        self.hf_status_label = QLabel()
        self.update_hf_status()
        hf_status_layout.addWidget(self.hf_status_label)

        # Кнопки управления
        hf_buttons = QHBoxLayout()
        self.hf_add_btn = QPushButton("Добавить ключ")
        self.hf_update_btn = QPushButton("Обновить ключ")
        self.hf_remove_btn = QPushButton("Удалить ключ")

        self.hf_add_btn.clicked.connect(lambda: self.add_key("huggingface"))
        self.hf_update_btn.clicked.connect(lambda: self.update_key("huggingface"))
        self.hf_remove_btn.clicked.connect(lambda: self.remove_key("huggingface"))

        hf_buttons.addWidget(self.hf_add_btn)
        hf_buttons.addWidget(self.hf_update_btn)
        hf_buttons.addWidget(self.hf_remove_btn)

        hf_layout.addLayout(hf_status_layout)
        hf_layout.addLayout(hf_buttons)
        hf_group.setLayout(hf_layout)

        # Добавляем группы в основной layout
        layout.addWidget(hf_group)

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)
        self.update_buttons_state()

    def update_hf_status(self):
        """Обновление статуса ключа Hugging Face"""
        key = self.settings.get_api_key("huggingface")
        if key:
            self.hf_status_label.setText("Статус: Ключ установлен")
            self.hf_status_label.setStyleSheet("color: green")
        else:
            self.hf_status_label.setText("Статус: Ключ не установлен")
            self.hf_status_label.setStyleSheet("color: red")

    def update_buttons_state(self):
        """Обновление состояния кнопок"""
        key = self.settings.get_api_key("huggingface")
        self.hf_add_btn.setEnabled(not key)
        self.hf_update_btn.setEnabled(bool(key))
        self.hf_remove_btn.setEnabled(bool(key))

    def add_key(self, service):
        """Добавление нового ключа"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Добавление ключа {service}")
            layout = QVBoxLayout()

            # Поле для ввода ключа
            key_label = QLabel("Введите API ключ:")
            key_input = QLineEdit()
            key_input.setEchoMode(QLineEdit.EchoMode.Password)

            # Кнопка показать/скрыть ключ
            show_key = QPushButton("Показать ключ")
            show_key.setCheckable(True)
            show_key.clicked.connect(lambda: key_input.setEchoMode(
                QLineEdit.EchoMode.Normal if show_key.isChecked()
                else QLineEdit.EchoMode.Password
            ))

            # Кнопки управления
            buttons = QHBoxLayout()
            save_btn = QPushButton("Сохранить")
            cancel_btn = QPushButton("Отмена")

            # Добавляем виджеты в layout
            layout.addWidget(key_label)
            layout.addWidget(key_input)
            layout.addWidget(show_key)
            buttons.addWidget(save_btn)
            buttons.addWidget(cancel_btn)
            layout.addLayout(buttons)

            dialog.setLayout(layout)

            # Подключаем обработчики
            save_btn.clicked.connect(dialog.accept)
            cancel_btn.clicked.connect(dialog.reject)

            # Показываем диалог
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_key = key_input.text().strip()
                if new_key:
                    # Сохраняем ключ
                    self.settings.set_api_key(service, new_key)
                    self.update_hf_status()
                    self.update_buttons_state()
                    QMessageBox.information(self, "Успех", "API ключ успешно сохранен")
                else:
                    QMessageBox.warning(self, "Ошибка", "API ключ не может быть пустым")

        except Exception as e:
            self.logger.error(f"Ошибка при добавлении ключа: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить API ключ: {str(e)}")

    def update_key(self, service):
        """Обновление существующего ключа"""
        try:
            current_key = self.settings.get_api_key(service)
            if not current_key:
                QMessageBox.warning(self, "Ошибка", "Ключ не найден")
                return

            dialog = QDialog(self)
            dialog.setWindowTitle(f"Обновление ключа {service}")
            layout = QVBoxLayout()

            # Поле для ввода ключа
            key_label = QLabel("Введите новый API ключ:")
            key_input = QLineEdit()
            key_input.setEchoMode(QLineEdit.EchoMode.Password)

            # Кнопка показать/скрыть ключ
            show_key = QPushButton("Показать ключ")
            show_key.setCheckable(True)
            show_key.clicked.connect(lambda: key_input.setEchoMode(
                QLineEdit.EchoMode.Normal if show_key.isChecked()
                else QLineEdit.EchoMode.Password
            ))

            # Кнопки управления
            buttons = QHBoxLayout()
            save_btn = QPushButton("Сохранить")
            cancel_btn = QPushButton("Отмена")

            # Добавляем виджеты в layout
            layout.addWidget(key_label)
            layout.addWidget(key_input)
            layout.addWidget(show_key)
            buttons.addWidget(save_btn)
            buttons.addWidget(cancel_btn)
            layout.addLayout(buttons)

            dialog.setLayout(layout)

            # Подключаем обработчики
            save_btn.clicked.connect(dialog.accept)
            cancel_btn.clicked.connect(dialog.reject)

            # Показываем диалог
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_key = key_input.text().strip()
                if new_key:
                    # Сохраняем ключ
                    self.settings.set_api_key(service, new_key)
                    self.update_hf_status()
                    self.update_buttons_state()
                    QMessageBox.information(self, "Успех", "API ключ успешно обновлен")
                else:
                    QMessageBox.warning(self, "Ошибка", "API ключ не может быть пустым")

        except Exception as e:
            self.logger.error(f"Ошибка при обновлении ключа: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить API ключ: {str(e)}")

    def remove_key(self, service):
        """Удаление ключа"""
        try:
            confirm = QMessageBox.question(
                self,
                "Подтверждение",
                f"Вы действительно хотите удалить ключ {service}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if confirm == QMessageBox.StandardButton.Yes:
                self.settings.remove_api_key(service)
                self.update_hf_status()
                self.update_buttons_state()
                QMessageBox.information(self, "Успех", "API ключ успешно удален")

        except Exception as e:
            self.logger.error(f"Ошибка при удалении ключа: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить API ключ: {str(e)}")
