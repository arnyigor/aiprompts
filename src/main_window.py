# main_window.py
import logging

from PyQt6.QtWidgets import QMainWindow, QListWidget, QVBoxLayout, QWidget, QPushButton, \
    QHBoxLayout, QLineEdit, QLabel, QMessageBox, QComboBox, QCheckBox
from PyQt6.QtCore import Qt

from src.preview import PromptPreview
from src.prompt_editor import PromptEditor
from src.prompt_manager import PromptManager
from src.settings import Settings
from src.api_keys_dialog import ApiKeysDialog


class MainWindow(QMainWindow):
    def __init__(self, prompt_manager: PromptManager, settings: Settings):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.prompt_manager = prompt_manager
        self.settings = settings
        self.setWindowTitle("Prompt Manager")
        self.setGeometry(100, 100, 800, 600)

        # Создаем меню
        self.create_menu()

        # Фильтры
        self.lang_filter = QComboBox()
        self.lang_filter.addItems(["Все", "RU", "EN"])
        
        # Фильтр избранного
        self.favorite_filter = QPushButton("⭐")
        self.favorite_filter.setCheckable(True)
        self.favorite_filter.setFixedWidth(30)
        self.favorite_filter.setToolTip("Показать избранное")
        
        # Сортировка
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["По названию", "По дате создания", "По категории"])
        self.sort_direction = QPushButton("↓")
        self.sort_direction.setFixedWidth(30)
        self.sort_direction.clicked.connect(self.toggle_sort_direction)
        self.sort_ascending = True

        # UI Components
        self.prompt_list = QListWidget()
        self.prompt_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)  # Множественный выбор
        self.search_field = QLineEdit()
        self.add_button = QPushButton("Добавить промпт")
        self.preview_button = QPushButton("Просмотр")
        self.edit_button = QPushButton("Редактировать")
        self.delete_button = QPushButton("Удалить")

        # Фильтр по категориям
        self.category_filter = QComboBox()
        self.category_filter.addItem("Все категории")
        
        # Фильтр по тегам
        self.tag_filter = QComboBox()
        self.tag_filter.addItem("Все теги")
        
        # Layout setup
        main_layout = QHBoxLayout()

        # Left panel (list + filters)
        left_layout = QVBoxLayout()
        
        # Search layout
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Поиск:"))
        search_layout.addWidget(self.search_field)
        left_layout.addLayout(search_layout)

        # Filters layout
        filters_layout = QHBoxLayout()
        # Language filter
        lang_layout = QVBoxLayout()
        lang_layout.addWidget(QLabel("Язык:"))
        lang_layout.addWidget(self.lang_filter)
        filters_layout.addLayout(lang_layout)
        
        # Favorite filter
        fav_layout = QVBoxLayout()
        fav_layout.addWidget(QLabel("Избранное:"))
        fav_layout.addWidget(self.favorite_filter)
        filters_layout.addLayout(fav_layout)
        
        # Category filter
        cat_layout = QVBoxLayout()
        cat_layout.addWidget(QLabel("Категория:"))
        cat_layout.addWidget(self.category_filter)
        filters_layout.addLayout(cat_layout)
        
        # Tag filter
        tag_layout = QVBoxLayout()
        tag_layout.addWidget(QLabel("Тег:"))
        tag_layout.addWidget(self.tag_filter)
        filters_layout.addLayout(tag_layout)
        
        left_layout.addLayout(filters_layout)

        # Sort layout
        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel("Сортировка:"))
        sort_layout.addWidget(self.sort_combo)
        sort_layout.addWidget(self.sort_direction)
        left_layout.addLayout(sort_layout)

        left_layout.addWidget(self.prompt_list)

        # Right panel (buttons)
        button_layout = QVBoxLayout()
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.preview_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()

        main_layout.addLayout(left_layout, 4)
        main_layout.addLayout(button_layout, 1)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Connect signals
        self.add_button.clicked.connect(self.open_editor)
        self.edit_button.clicked.connect(self.edit_selected)
        self.delete_button.clicked.connect(self.delete_selected)
        self.search_field.textChanged.connect(self.filter_prompts)
        self.lang_filter.currentTextChanged.connect(self.filter_prompts)
        self.favorite_filter.clicked.connect(self.filter_prompts)
        self.category_filter.currentTextChanged.connect(self.filter_prompts)
        self.tag_filter.currentTextChanged.connect(self.filter_prompts)
        self.sort_combo.currentTextChanged.connect(self.filter_prompts)
        self.prompt_list.itemDoubleClicked.connect(self.edit_selected)
        self.preview_button.clicked.connect(self.preview_selected)

        # Load initial data
        self.load_prompts()

    def create_menu(self):
        """Создание главного меню"""
        menubar = self.menuBar()
        
        # Меню Файл
        file_menu = menubar.addMenu("Файл")
        
        # Пункт API ключи
        api_keys_action = file_menu.addAction("API ключи")
        api_keys_action.triggered.connect(self.show_api_keys_dialog)
        
        # Разделитель
        file_menu.addSeparator()
        
        # Пункт Выход
        exit_action = file_menu.addAction("Выход")
        exit_action.triggered.connect(self.close)

    def toggle_sort_direction(self):
        """Переключение направления сортировки"""
        self.sort_ascending = not self.sort_ascending
        self.sort_direction.setText("↓" if self.sort_ascending else "↑")
        self.filter_prompts()

    def load_prompts(self):
        """Загрузка промптов в список с обновлением фильтров"""
        # Блокируем сигналы на время обновления
        self.category_filter.blockSignals(True)
        self.tag_filter.blockSignals(True)
        self.lang_filter.blockSignals(True)
        self.sort_combo.blockSignals(True)
        
        try:
            self.prompt_list.clear()
            prompts = self.prompt_manager.list_prompts()
            self.logger.debug(f"load_prompts: Получено промптов: {len(prompts)}")
            
            # Сортируем промпты по названию (начальная сортировка)
            prompts.sort(key=lambda x: x.title.lower(), reverse=not self.sort_ascending)
            
            # Добавляем отсортированные промпты в список
            for prompt in prompts:
                item_text = f"{prompt.title} ({prompt.id})"
                self.prompt_list.addItem(item_text)
            
            # Проверяем, что промпты добавились
            self.logger.debug(f"load_prompts: Количество элементов в списке: {self.prompt_list.count()}")
            
            # Обновляем список категорий
            categories = set()
            tags = set()
            for prompt in prompts:
                categories.add(prompt.category)
                if hasattr(prompt, 'tags'):
                    tags.update(prompt.tags)
            
            self.logger.debug(f"load_prompts: Найдено категорий: {len(categories)}")
            self.logger.debug(f"load_prompts: Найдено тегов: {len(tags)}")
            
            # Сохраняем текущие выбранные значения
            current_category = self.category_filter.currentText()
            current_tag = self.tag_filter.currentText()
            
            # Обновляем списки фильтров
            self.category_filter.clear()
            self.category_filter.addItem("Все категории")
            self.category_filter.addItems(sorted(categories))
            
            self.tag_filter.clear()
            self.tag_filter.addItem("Все теги")
            self.tag_filter.addItems(sorted(tags))
            
            # Восстанавливаем выбранные значения
            index = self.category_filter.findText(current_category)
            if index >= 0:
                self.category_filter.setCurrentIndex(index)
                
            index = self.tag_filter.findText(current_tag)
            if index >= 0:
                self.tag_filter.setCurrentIndex(index)
            
            # Устанавливаем начальную сортировку в комбобоксе
            self.sort_combo.setCurrentText("По названию")
            
            # Обновляем заголовок окна со статистикой
            total_prompts = len(prompts)
            self.setWindowTitle(f"Prompt Manager - Загружено промптов: {total_prompts}")
            
        finally:
            # Разблокируем сигналы
            self.category_filter.blockSignals(False)
            self.tag_filter.blockSignals(False)
            self.lang_filter.blockSignals(False)
            self.sort_combo.blockSignals(False)

    def filter_prompts(self):
        """Фильтрация и сортировка промптов"""
        try:
            # Получаем все промпты
            prompts = self.prompt_manager.list_prompts()
            # self.logger.debug(f"filter_prompts: Начало фильтрации, всего промптов: {len(prompts)}")
            filtered_prompts = []
            
            # Применяем фильтры
            search_query = self.search_field.text().lower()
            category_filter = self.category_filter.currentText()
            lang_filter = self.lang_filter.currentText()
            tag_filter = self.tag_filter.currentText()
            show_favorites = self.favorite_filter.isChecked()
            
            # self.logger.debug(f"filter_prompts: Параметры фильтрации: поиск='{search_query}', категория='{category_filter}', тег='{tag_filter}', язык='{lang_filter}', избранное={show_favorites}")
            
            for prompt in prompts:
                # Проверяем все условия фильтрации
                matches = True
                
                # Фильтр по избранному
                if show_favorites and not getattr(prompt, 'is_favorite', False):
                    matches = False
                
                # Фильтр по поисковому запросу
                if search_query:
                    if not (search_query in prompt.title.lower() or 
                          search_query in prompt.content.get('ru', '').lower() or 
                          search_query in prompt.content.get('en', '').lower()):
                        matches = False
                
                # Фильтр по категории
                if category_filter != "Все категории" and prompt.category != category_filter:
                    matches = False
                
                # Фильтр по тегам
                if tag_filter != "Все теги":
                    if not hasattr(prompt, 'tags') or tag_filter not in prompt.tags:
                        matches = False
                
                # Фильтр по языку
                if lang_filter != "Все":
                    if lang_filter == "RU" and not prompt.content.get('ru'):
                        matches = False
                    elif lang_filter == "EN" and not prompt.content.get('en'):
                        matches = False
                
                if matches:
                    filtered_prompts.append(prompt)
            
            self.logger.debug(f"filter_prompts: После фильтрации осталось промптов: {len(filtered_prompts)}")
            
            # Применяем сортировку
            sort_type = self.sort_combo.currentText()
            reverse = not self.sort_ascending
            
            if sort_type == "По названию":
                filtered_prompts.sort(key=lambda x: x.title.lower(), reverse=reverse)
            elif sort_type == "По дате создания":
                filtered_prompts.sort(key=lambda x: x.created_at, reverse=reverse)
            elif sort_type == "По категории":
                filtered_prompts.sort(key=lambda x: x.category.lower(), reverse=reverse)
            
            # Обновляем список
            self.prompt_list.clear()
            for prompt in filtered_prompts:
                item_text = f"{prompt.title} ({prompt.id})"
                self.prompt_list.addItem(item_text)
            
            # Проверяем, что промпты добавились после фильтрации
            # self.logger.debug(f"filter_prompts: Количество элементов в списке после фильтрации: {self.prompt_list.count()}")
            
            # Обновляем статистику
            total_prompts = len(prompts)
            filtered_count = len(filtered_prompts)
            self.setWindowTitle(f"Prompt Manager - Показано {filtered_count} из {total_prompts}")
            
        except Exception as e:
            self.logger.error(f"Ошибка фильтрации: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось выполнить фильтрацию: {str(e)}")

    def preview_selected(self):
        """Открытие предпросмотра"""
        selected_items = self.prompt_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите промпт для просмотра")
            return

        # Подтверждение при большом количестве выбранных промптов
        if len(selected_items) > 3:
            confirm = QMessageBox.question(
                self,
                "Подтверждение",
                f"Вы выбрали {len(selected_items)} промптов для просмотра.\n"
                "Будет открыто несколько окон предпросмотра.\n\n"
                "Продолжить?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return

        try:
            for item in selected_items:
                prompt_id = item.text().split('(')[-1].rstrip(')')
                prompt = self.prompt_manager.get_prompt(prompt_id)
                if prompt:
                    preview = PromptPreview(prompt)
                    preview.exec()
                else:
                    QMessageBox.warning(self, "Ошибка", f"Промпт {prompt_id} не найден")
        except Exception as e:
            self.logger.error(f"Ошибка предпросмотра: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", "Не удалось открыть предпросмотр")

    def open_editor(self):
        self.logger.debug("Открытие редактора...")
        try:
            editor = PromptEditor(self.prompt_manager, self.settings)
            if editor.exec():
                self.logger.info("Данные сохранены, обновление списка")
                self.load_prompts()
        except Exception as e:
            self.logger.error("Ошибка в редакторе", exc_info=True)
            QMessageBox.critical(self, "Ошибка", "Не удалось открыть редактор")

    def edit_selected(self):
        """Редактирование выбранных промптов"""
        selected_items = self.prompt_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите промпты для редактирования")
            return

        try:
            # Подготовка списка промптов для редактирования
            prompts_to_edit = []
            for item in selected_items:
                prompt_id = item.text().split('(')[-1].rstrip(')')
                prompt = self.prompt_manager.get_prompt(prompt_id)
                if prompt:
                    prompts_to_edit.append((prompt_id, prompt.title))

            # Подтверждение редактирования
            message = "Будут отредактированы следующие промпты:\n\n"
            if len(prompts_to_edit) > 5:
                message += f"Всего выбрано: {len(prompts_to_edit)} промптов\n"
                message += "Первые 5 промптов:\n"
                for prompt_id, title in prompts_to_edit[:5]:
                    message += f"- {title} ({prompt_id})\n"
                message += "...\n\n"
                message += "Внимание: Будет открыто несколько окон редактирования.\n"
                message += "Рекомендуется редактировать не более 5 промптов за раз."
            else:
                for prompt_id, title in prompts_to_edit:
                    message += f"- {title} ({prompt_id})\n"

            confirm = QMessageBox.question(
                self,
                "Подтверждение редактирования",
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return

            # Редактирование промптов
            edited_count = 0
            for prompt_id, title in prompts_to_edit:
                editor = PromptEditor(self.prompt_manager, self.settings, prompt_id)
                if editor.exec():
                    self.logger.info(f"Промпт {prompt_id} успешно отредактирован")
                    edited_count += 1
                else:
                    self.logger.debug(f"Редактирование промпта {prompt_id} отменено пользователем")

            # Отображаем сообщение только если были реальные изменения
            if edited_count > 0:
                QMessageBox.information(
                    self,
                    "Успешно",
                    f"Отредактировано промптов: {edited_count}"
                )
            
            # Обновляем список только если были изменения
            if edited_count > 0:
                self.load_prompts()

        except Exception as e:
            self.logger.error(f"Ошибка при редактировании: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", "Не удалось выполнить редактирование")

    def delete_selected(self):
        """Удаление выбранных промптов"""
        selected_items = self.prompt_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите промпты для удаления")
            return

        try:
            # Подготовка списка промптов для удаления
            prompts_to_delete = []
            for item in selected_items:
                prompt_id = item.text().split('(')[-1].rstrip(')')
                prompt = self.prompt_manager.get_prompt(prompt_id)
                if prompt:
                    prompts_to_delete.append((prompt_id, prompt.title))

            # Подтверждение удаления
            message = "ВНИМАНИЕ: Это действие нельзя отменить!\n\n"
            message += "Будут удалены следующие промпты:\n\n"
            if len(prompts_to_delete) > 10:
                message += f"Всего выбрано: {len(prompts_to_delete)} промптов\n"
                message += "Первые 10 промптов:\n"
                for prompt_id, title in prompts_to_delete[:10]:
                    message += f"- {title} ({prompt_id})\n"
                message += "...\n"
            else:
                for prompt_id, title in prompts_to_delete:
                    message += f"- {title} ({prompt_id})\n"

            # Двойное подтверждение при удалении большого количества промптов
            if len(prompts_to_delete) > 10:
                pre_confirm = QMessageBox.warning(
                    self,
                    "Внимание",
                    f"Вы собираетесь удалить {len(prompts_to_delete)} промптов.\n"
                    "Это большое количество промптов для удаления.\n\n"
                    "Хотите продолжить?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if pre_confirm != QMessageBox.StandardButton.Yes:
                    return

            confirm = QMessageBox.question(
                self,
                "Подтверждение удаления",
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if confirm == QMessageBox.StandardButton.Yes:
                # Финальное подтверждение
                final_confirm = QMessageBox.warning(
                    self,
                    "Финальное подтверждение",
                    "Вы действительно хотите удалить выбранные промпты?\n"
                    "Это действие НЕЛЬЗЯ отменить!",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if final_confirm == QMessageBox.StandardButton.Yes:
                    # Удаление промптов
                    deleted_count = 0
                    failed_count = 0
                    for prompt_id, _ in prompts_to_delete:
                        try:
                            self.prompt_manager.delete_prompt(prompt_id)
                            deleted_count += 1
                        except Exception as e:
                            self.logger.error(f"Ошибка удаления промпта {prompt_id}: {str(e)}")
                            failed_count += 1

                    # Отображение результатов
                    if failed_count == 0:
                        QMessageBox.information(
                            self,
                            "Успешно",
                            f"Удалено промптов: {deleted_count}"
                        )
                    else:
                        QMessageBox.warning(
                            self,
                            "Внимание",
                            f"Удалено промптов: {deleted_count}\n"
                            f"Не удалось удалить: {failed_count}"
                        )

                    self.load_prompts()

        except Exception as e:
            self.logger.error(f"Ошибка при удалении: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", "Не удалось выполнить удаление")

    def show_api_keys_dialog(self):
        dialog = ApiKeysDialog(self.settings, self)
        dialog.exec()
