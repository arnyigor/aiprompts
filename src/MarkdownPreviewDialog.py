# markdown_viewer.py
import markdown
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTextBrowser, QPushButton,
                             QStackedWidget, QTextEdit, QHBoxLayout, QWidget)


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

        # 1. Виджет для отформатированного текста (как и был)
        self.rendered_view = QTextBrowser()
        html = markdown.markdown(self.markdown_text, extensions=['fenced_code', 'tables', 'codehilite'])
        self.rendered_view.setHtml(html)
        self.rendered_view.setOpenExternalLinks(True)

        # 2. Виджет для исходного кода Markdown
        self.raw_view = QTextEdit()
        self.raw_view.setPlainText(self.markdown_text)
        self.raw_view.setReadOnly(True)  # Делаем его нередактируемым
        # Устанавливаем моноширинный шрифт для лучшей читаемости кода
        font = QFont("Courier New", 10)
        self.raw_view.setFont(font)

        # --- Создание QStackedWidget для управления видами ---
        self.view_stack = QStackedWidget()
        self.view_stack.addWidget(self.rendered_view)  # Индекс 0
        self.view_stack.addWidget(self.raw_view)  # Индекс 1

        # --- Создание кнопок ---

        # Кнопка для переключения вида
        self.toggle_button = QPushButton("Показать исходный код")
        self.toggle_button.clicked.connect(self.toggle_view)

        # Кнопка закрытия
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.accept)

        # --- Компоновка ---

        # Горизонтальный layout для кнопок
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.toggle_button)
        button_layout.addStretch()  # Растягиваем пространство, чтобы кнопка "Закрыть" была справа
        button_layout.addWidget(close_button)

        # Основной вертикальный layout
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.view_stack)  # Добавляем наш переключатель видов
        main_layout.addLayout(button_layout)  # Добавляем layout с кнопками

    def toggle_view(self):
        """
        Переключает вид между отформатированным текстом и исходным кодом.
        """
        current_index = self.view_stack.currentIndex()

        if current_index == 0:  # Если сейчас показан отформатированный вид (индекс 0)
            # Переключаемся на исходный код (индекс 1)
            self.view_stack.setCurrentIndex(1)
            self.toggle_button.setText("Показать форматирование")
        else:  # Если сейчас показан исходный код (индекс 1)
            # Переключаемся на отформатированный вид (индекс 0)
            self.view_stack.setCurrentIndex(0)
            self.toggle_button.setText("Показать исходный код")
