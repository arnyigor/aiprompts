# markdown_viewer.py
import markdown
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTextBrowser, QPushButton,
                             QStackedWidget, QTextEdit, QHBoxLayout, QWidget)

# ДОБАВЛЕНО: CSS-стили для корректного отображения Markdown-элементов
CSS_STYLES = """
<style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        font-size: 16px;
        line-height: 1.6;
        color: #333;
        background-color: #fff;
    }
    h1, h2, h3, h4, h5, h6 {
        margin-top: 24px;
        margin-bottom: 16px;
        font-weight: 600;
        line-height: 1.25;
    }
    h1 { font-size: 2em; }
    h2 { font-size: 1.5em; }
    h3 { font-size: 1.25em; }
    
    /* Стили для таблиц */
    table {
        border-collapse: collapse;
        width: 100%;
        margin-top: 16px;
        margin-bottom: 16px;
        display: block; /* Важно для QTextBrowser */
        overflow-x: auto; /* Для широких таблиц */
    }
    th, td {
        border: 1px solid #dfe2e5;
        padding: 8px 12px;
    }
    th {
        font-weight: 600;
        background-color: #f6f8fa;
    }
    tr:nth-child(2n) {
        background-color: #f6f8fa;
    }

    /* Стили для блоков кода */
    pre {
        background-color: #f6f8fa;
        border-radius: 6px;
        padding: 16px;
        overflow: auto;
        font-size: 85%;
        line-height: 1.45;
    }
    code {
        font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
    }
    pre > code {
        padding: 0;
        margin: 0;
        font-size: 100%;
        word-break: normal;
        white-space: pre;
        background: transparent;
        border: 0;
    }
    
    /* Стили для подсветки синтаксиса от Pygments (если используется codehilite) */
    .codehilite {
        background: #f6f8fa; /* Цвет фона для всего блока */
        border-radius: 6px;
    }
    .codehilite pre {
        margin: 0; /* Убираем лишние отступы, если они есть */
    }

    /* Цитаты */
    blockquote {
        border-left: 0.25em solid #dfe2e5;
        color: #6a737d;
        padding: 0 1em;
        margin-left: 0;
    }
    
    /* Списки */
    ul, ol {
        padding-left: 2em;
    }
</style>
"""


class MarkdownPreviewDialog(QDialog):
    """
    Диалоговое окно для просмотра текста в формате Markdown
    с возможностью переключения на исходный код.
    """

    def __init__(self, markdown_text: str, window_title: str = "Просмотр Markdown", parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle(window_title)
        self.setGeometry(400, 400, 700, 500)
        self.setMinimumSize(500, 400)

        # Сохраняем исходный текст, он нам понадобится для второй вкладки
        self.markdown_text = markdown_text

        # --- Создание виджетов для переключения ---

        # 1. Виджет для отформатированного текста
        self.rendered_view = QTextBrowser()
        self.rendered_view.setOpenExternalLinks(True)

        # --- ИЗМЕНЕНО: Генерация HTML с внедрением CSS ---
        # Преобразуем Markdown в HTML-фрагмент
        # Добавляем расширения для поддержки таблиц, блоков кода и подсветки синтаксиса
        # Убедитесь, что у вас установлена библиотека Pygments: pip install Pygments
        md_extensions = ['fenced_code', 'tables', 'codehilite']
        html_body = markdown.markdown(self.markdown_text, extensions=md_extensions)

        # Собираем полный HTML-документ со стилями
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            {CSS_STYLES}
        </head>
        <body>
            {html_body}
        </body>
        </html>
        """
        self.rendered_view.setHtml(full_html)
        # --- Конец изменений ---

        # 2. Виджет для исходного кода Markdown
        self.raw_view = QTextEdit()
        self.raw_view.setPlainText(self.markdown_text)
        self.raw_view.setReadOnly(True)
        font = QFont("Courier New", 10)
        self.raw_view.setFont(font)

        # --- Создание QStackedWidget для управления видами ---
        self.view_stack = QStackedWidget()
        self.view_stack.addWidget(self.rendered_view)  # Индекс 0
        self.view_stack.addWidget(self.raw_view)  # Индекс 1

        # --- Создание кнопок ---
        self.toggle_button = QPushButton("Показать исходный код")
        self.toggle_button.clicked.connect(self.toggle_view)

        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.accept)

        # --- Компоновка ---
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.toggle_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.view_stack)
        main_layout.addLayout(button_layout)

    def toggle_view(self):
        """
        Переключает вид между отформатированным текстом и исходным кодом.
        """
        current_index = self.view_stack.currentIndex()

        if current_index == 0:
            self.view_stack.setCurrentIndex(1)
            self.toggle_button.setText("Показать форматирование")
        else:
            self.view_stack.setCurrentIndex(0)
            self.toggle_button.setText("Показать исходный код")
