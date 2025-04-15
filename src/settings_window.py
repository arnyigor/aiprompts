from PyQt6.QtCore import QSettings, pyqtSignal
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton, QMessageBox, QFileDialog

class SettingsDialog(QDialog):
    settings_changed = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        # Инициализация компонентов
        layout = QVBoxLayout()

        # Поле для выбора пути к папке prompts
        self.prompts_path_label = QLabel(self.tr("Путь к папке prompts"))
        self.prompts_path_edit = QLineEdit()
        self.load_settings()  # Загрузка сохраненных настроек
        self.browse_button = QPushButton(self.tr("Обзор"))
        self.browse_button.clicked.connect(self.browse_prompts_path)

        prompts_path_layout = QHBoxLayout()
        prompts_path_layout.addWidget(self.prompts_path_label)
        prompts_path_layout.addWidget(self.prompts_path_edit)
        prompts_path_layout.addWidget(self.browse_button)
        layout.addLayout(prompts_path_layout)

        # Кнопка сохранения настроек
        save_button = QPushButton(self.tr("Сохранить"))
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

        self.setLayout(layout)

    def load_settings(self):
        settings = QSettings("YourCompany", "YourApp")
        self.prompts_path_edit.setText(settings.value("prompts_path", "."))  # По умолчанию корень проекта

    def accept(self):
        # Испускаем сигнал об успешном сохранении настроек
        self.settings_changed.emit()
        super().accept()

    def save_settings(self):
        settings = QSettings("YourCompany", "YourApp")
        settings.setValue("prompts_path", self.prompts_path_edit.text())
        QMessageBox.information(self, self.tr("Успех"), self.tr("Настройки сохранены"))
        self.accept()

    def browse_prompts_path(self):
        directory = QFileDialog.getExistingDirectory(self, self.tr("Выберите папку prompts"),
                                                     self.prompts_path_edit.text())
        if directory:
            self.prompts_path_edit.setText(directory)
