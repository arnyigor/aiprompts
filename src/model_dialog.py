from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, \
    QDialogButtonBox, QVBoxLayout


class ModelConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Конфигурация модели")

        layout = QFormLayout()

        self.name = QLineEdit()
        self.provider = QComboBox()
        self.provider.addItems(["OpenAI", "Anthropic", "Google", "Meta", "Mistral AI"])

        self.max_tokens = QSpinBox()
        self.max_tokens.setRange(1, 32000)
        self.max_tokens.setValue(2000)

        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0, 2)
        self.temperature.setValue(0.7)
        self.temperature.setSingleStep(0.1)

        layout.addRow("Название:", self.name)
        layout.addRow("Провайдер:", self.provider)
        layout.addRow("Max tokens:", self.max_tokens)
        layout.addRow("Temperature:", self.temperature)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addWidget(buttons)
        self.setLayout(main_layout)

    def get_config(self) -> dict:
        return {
            "name": self.name.text(),
            "provider": self.provider.currentText(),
            "max_tokens": self.max_tokens.value(),
            "temperature": self.temperature.value()
        }
