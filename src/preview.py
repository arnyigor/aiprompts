# ui/preview.py
from PyQt6.QtWidgets import QDialog, QTextEdit, QVBoxLayout, QLabel


class PromptPreview(QDialog):
    def __init__(self, prompt_data: dict):
        super().__init__()
        self.setWindowTitle("Предпросмотр промпта")
        self.setGeometry(300, 300, 500, 400)

        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"<h2>{prompt_data['title']}</h2>"))
        layout.addWidget(QLabel(f"Описание: {prompt_data['description']}"))
        layout.addWidget(QLabel(f"Контент:"))
        content = QTextEdit(prompt_data['content'])
        content.setReadOnly(True)
        layout.addWidget(content)
        layout.addWidget(QLabel(f"Переменные:"))
        for var in prompt_data['variables']:
            layout.addWidget(QLabel(f"- {var['name']} ({var['type']}): {var['description']}"))

        self.setLayout(layout)