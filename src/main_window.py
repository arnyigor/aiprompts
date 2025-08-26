# main_window.py
import logging
import os
from pathlib import Path

from PyQt6.QtCore import pyqtSlot, QThread, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMainWindow, QListWidget, QPushButton, \
    QLineEdit, QLabel, QMessageBox, QComboBox, QProgressDialog
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout

from api_keys_dialog import ApiKeysDialog
from  feedback_dialog import FeedbackDialog
from feedback_sender import send_feedback
from llm_settings import Settings
from preview import PromptPreview
from prompt_editor import PromptEditor
from prompt_manager import PromptManager
from settings_window import SettingsDialog
from sync_log_dialog import SyncLogDialog
from sync_manager import SyncManager
from sync_worker import SyncWorker

APP_INFO = {
    "name": "Prompt Manager Python",
    "id": "prompt-manager-python",
    "version": "1.0.0",
    "packagename": "com.arny.promptmanager"
}


class MainWindow(QMainWindow):
    def __init__(self, prompt_manager: PromptManager, settings: Settings):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.prompt_manager = prompt_manager
        self.settings = settings
        self.app_info = APP_INFO
        self.setWindowTitle("Prompt Manager")
        self.setGeometry(100, 100, 800, 600)

        # Установка иконки приложения (от корня проекта)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(project_root, "assets", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.logger.warning(f"Icon not found at {icon_path}")

        # Фильтры
        self.lang_filter = QComboBox()
        self.lang_filter.addItems(["Все", "RU", "EN"])

        # Фильтр избранного
        self.favorite_filter = QPushButton("⭐")
        self.favorite_filter.setCheckable(True)
        self.favorite_filter.setFixedWidth(30)
        self.favorite_filter.setToolTip("Показать избранное")

        # Фильтр только локальные
        self.local_filter = QPushButton("🏠")
        self.local_filter.setCheckable(True)
        self.local_filter.setFixedWidth(30)
        self.local_filter.setToolTip("Показать только локальные")

        # Сортировка
        # Список вариантов сортировки правильной очередностью
        self.SORT_OPTIONS = [
            "Сначала избранное",
            "По названию",
            "По дате создания",
            "По категории"
        ]
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(self.SORT_OPTIONS)
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

        # объект менеджера
        self.sync_button = QPushButton("🔄 Синхронизация")
        self.sync_button.clicked.connect(self.run_sync)

        # Инициализация компонентов
        self.settings_button = QPushButton("⚙️")
        self.settings_button.setToolTip("Настройки")
        self.settings_button.adjustSize()
        self.settings_button.clicked.connect(self.show_settings_dialog)

        self.feedback_button = QPushButton("✉️ Обратная связь")
        self.feedback_button.setToolTip("Отправить отзыв или сообщить о проблеме")

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

        # Local filter
        local_layout = QVBoxLayout()
        local_layout.addWidget(QLabel("Локальные:"))
        local_layout.addWidget(self.local_filter)
        filters_layout.addLayout(local_layout)

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
        button_layout.addWidget(self.sync_button)
        button_layout.addWidget(self.feedback_button)
        button_layout.addWidget(self.settings_button)

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
        self.local_filter.clicked.connect(self.filter_prompts)
        self.category_filter.currentTextChanged.connect(self.filter_prompts)
        self.tag_filter.currentTextChanged.connect(self.filter_prompts)
        self.sort_combo.currentTextChanged.connect(self.filter_prompts)
        self.prompt_list.itemDoubleClicked.connect(self.show_action_dialog)
        self.preview_button.clicked.connect(self.preview_selected)
        self.feedback_button.clicked.connect(self.show_feedback_dialog)

        # Load initial data
        self.load_prompts()

    def run_sync(self):
        # 1. Создаем диалог для логов
        self._sync_log_dialog = SyncLogDialog(self)

        # 2. ОПРЕДЕЛЯЕМ ПАРАМЕТРЫ И СОЗДАЕМ SYNC_MANAGER ЗДЕСЬ!
        prompts_dir = Path(self.prompt_manager.storage_path)

        # Создаем экземпляр SyncManager, передавая ему путь и ОБЪЕКТ НАСТРОЕК
        sync_manager = SyncManager(
            storage=self.prompt_manager.storage, # <-- ПЕРЕДАЕМ LocalStorage
            settings=self.settings
        )

        # 3. Создаем воркер и передаем ему только что созданный менеджер
        self._sync_thread = QThread(self)
        worker = SyncWorker(sync_manager)
        worker.moveToThread(self._sync_thread)

        # 4. Соединяем сигналы с колбэками диалога
        # (Это работает, потому что колбэки уже встроены в SyncWorker/SyncManager)
        worker.progress.connect(self._sync_log_dialog.set_status)
        worker.log_message.connect(self._sync_log_dialog.add_log_message)
        worker.finished.connect(self._on_sync_finished)

        # 5. Запускаем поток и показываем диалог
        self._sync_thread.started.connect(worker.run)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(self._sync_thread.quit)
        self._sync_thread.finished.connect(self._sync_thread.deleteLater)

        self._sync_thread.start()
        self.sync_button.setEnabled(False)
        self._sync_log_dialog.exec()

    @pyqtSlot(bool, str)
    def _on_sync_finished(self, ok: bool, msg: str):
        # 1. Разблокируем кнопку и делаем диалог завершенным
        self.sync_button.setEnabled(True)
        if hasattr(self, '_sync_log_dialog'):
            self._sync_log_dialog.mark_as_finished()
            # Диалог закроется сам по нажатию "Ок" пользователем.
            # Если хотите закрывать автоматически, можно вызвать self._sync_log_dialog.accept()

        # 2. Обновляем данные и показываем финальное сообщение
        if ok:
            self.load_prompts()
            # Финальное сообщение можно не показывать, т.к. лог уже есть
            # QMessageBox.information(self, "Синхронизация", msg)
        else:
            QMessageBox.critical(self, "Синхронизация", msg)

    @pyqtSlot()
    def show_feedback_dialog(self):
        """
        Открывает диалог для отправки обратной связи.
        """
        dialog = FeedbackDialog(self)
        # exec() - модальный вызов, блокирует основное окно
        if dialog.exec():
            feedback_text = dialog.get_feedback_text()
            if not feedback_text:
                QMessageBox.warning(self, "Внимание", "Сообщение не может быть пустым.")
                return

            # Отправляем сообщение
            # Внимание: эта операция может "заморозить" UI, если сеть медленная.
            # Для продакшн-приложений лучше выполнять в отдельном потоке.
            success = send_feedback(feedback_text, self.app_info)

            if success:
                QMessageBox.information(
                    self,
                    "Спасибо!",
                    "Ваше сообщение успешно отправлено. Спасибо за обратную связь!"
                )
            else:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    "Не удалось отправить сообщение. "
                    "Пожалуйста, проверьте ваше интернет-соединение и попробуйте позже."
                )

    # Метод для отображения диалога настроек
    def show_settings_dialog(self):
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self.settings_changed)
        dialog.exec()

    @pyqtSlot()
    def settings_changed(self):
        self.logger.debug("Обнаружены изменения в настройках")
        self.prompt_manager = PromptManager()
        self.load_prompts()

    def toggle_sort_direction(self):
        """Переключение направления сортировки"""
        self.sort_ascending = not self.sort_ascending
        self.sort_direction.setText("↓" if self.sort_ascending else "↑")
        self.filter_prompts()

    def save_filter_state(self):
        """Сохранение текущего состояния фильтров"""
        return {
            'search': self.search_field.text(),
            'category': self.category_filter.currentText(),
            'tag': self.tag_filter.currentText(),
            'lang': self.lang_filter.currentText(),
            'favorite': self.favorite_filter.isChecked(),
            'local': self.local_filter.isChecked(),
            'sort': self.sort_combo.currentText(),
            'sort_direction': self.sort_ascending
        }

    def restore_filter_state(self, state):
        """Восстановление состояния фильтров"""
        self.search_field.setText(state['search'])
        index = self.category_filter.findText(state['category'])
        if index >= 0:
            self.category_filter.setCurrentIndex(index)
        index = self.tag_filter.findText(state['tag'])
        if index >= 0:
            self.tag_filter.setCurrentIndex(index)
        index = self.lang_filter.findText(state['lang'])
        if index >= 0:
            self.lang_filter.setCurrentIndex(index)
        self.favorite_filter.setChecked(state['favorite'])
        self.local_filter.setChecked(state.get('local', False))  # По умолчанию False для обратной совместимости
        index = self.sort_combo.findText(state['sort'])
        if index >= 0:
            self.sort_combo.setCurrentIndex(index)
        self.sort_ascending = state['sort_direction']
        self.sort_direction.setText("↓" if self.sort_ascending else "↑")

    def load_prompts(self):
        """Загрузка промптов в список с сохранением фильтров"""
        # Сохраняем текущее состояние фильтров
        filter_state = self.save_filter_state()

        try:
            # Блокируем сигналы на время обновления
            self.category_filter.blockSignals(True)
            self.tag_filter.blockSignals(True)
            self.lang_filter.blockSignals(True)
            self.sort_combo.blockSignals(True)

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

            # Обновляем списки фильтров
            self.category_filter.clear()
            self.category_filter.addItem("Все категории")
            self.category_filter.addItems(sorted(categories))

            self.tag_filter.clear()
            self.tag_filter.addItem("Все теги")
            self.tag_filter.addItems(sorted(tags))

            # Восстанавливаем состояние фильтров
            self.restore_filter_state(filter_state)

            # Обновляем заголовок окна со статистикой
            total_prompts = len(prompts)
            self.setWindowTitle(f"Prompt Manager - Загружено промптов: {total_prompts}")

        finally:
            # Разблокируем сигналы
            self.category_filter.blockSignals(False)
            self.tag_filter.blockSignals(False)
            self.lang_filter.blockSignals(False)
            self.sort_combo.blockSignals(False)

            # Применяем фильтры к обновленному списку
            self.filter_prompts()

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
            show_local_only = self.local_filter.isChecked()

            # self.logger.debug(f"filter_prompts: Параметры фильтрации: поиск='{search_query}', категория='{category_filter}', тег='{tag_filter}', язык='{lang_filter}', избранное={show_favorites}")

            for prompt in prompts:
                # Проверяем все условия фильтрации
                matches = True

                # Фильтр по избранному
                if show_favorites and not getattr(prompt, 'is_favorite', False):
                    matches = False

                # Фильтр по локальным
                if show_local_only and not getattr(prompt, 'is_local', True):
                    matches = False

                # Фильтр по поисковому запросу
                if search_query:
                    content_text = ""
                    if isinstance(prompt.content, dict):
                        content_text = prompt.content.get('ru', '') + " " + prompt.content.get('en', '')
                    else:
                        content_text = str(prompt.content)

                    if not (search_query in prompt.title.lower() or
                            search_query in content_text.lower()):
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
                    if isinstance(prompt.content, dict):
                        if lang_filter == "RU" and not prompt.content.get('ru'):
                            matches = False
                        elif lang_filter == "EN" and not prompt.content.get('en'):
                            matches = False
                    else:
                        # Если content - строка, то считаем что подходит для любого языка
                        pass

                if matches:
                    filtered_prompts.append(prompt)

            self.logger.debug(f"filter_prompts: После фильтрации осталось промптов: {len(filtered_prompts)}")

            # Применяем сортировку
            sort_type = self.sort_combo.currentText()
            reverse = not self.sort_ascending

            sort_strategies = {
                self.SORT_OPTIONS[0]: lambda x: (not x.is_favorite, x.title.lower()),  # Сначала избранное
                self.SORT_OPTIONS[1]: lambda x: x.title.lower(),  # По названию
                self.SORT_OPTIONS[2]: lambda x: x.created_at,  # По дате создания
                self.SORT_OPTIONS[3]: lambda x: x.category.lower()  # По категории
            }
            filtered_prompts.sort(key=sort_strategies[sort_type], reverse=reverse)

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
                    preview = PromptPreview(prompt, self.settings)
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

    def show_action_dialog(self, item):
        """Показывает диалог выбора действия при двойном клике"""
        prompt_id = item.text().split('(')[-1].rstrip(')')
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Выберите действие")
        dialog.setText(f"Выберите действие для промпта:\n{item.text()}")
        edit_button = dialog.addButton("Редактировать", QMessageBox.ButtonRole.AcceptRole)
        preview_button = dialog.addButton("Просмотреть", QMessageBox.ButtonRole.AcceptRole)
        dialog.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)

        dialog.exec()
        clicked_button = dialog.clickedButton()

        if clicked_button == edit_button:
            try:
                editor = PromptEditor(self.prompt_manager, self.settings, prompt_id)
                if editor.exec():
                    self.load_prompts()
            except Exception as e:
                self.logger.error(f"Ошибка при редактировании: {str(e)}", exc_info=True)
                QMessageBox.critical(self, "Ошибка", "Не удалось открыть редактор")
        elif clicked_button == preview_button:
            try:
                prompt = self.prompt_manager.get_prompt(prompt_id)
                if prompt:
                    preview = PromptPreview(prompt, self.settings)
                    preview.exec()
                else:
                    QMessageBox.warning(self, "Ошибка", f"Промпт {prompt_id} не найден")
            except Exception as e:
                self.logger.error(f"Ошибка предпросмотра: {str(e)}", exc_info=True)
                QMessageBox.critical(self, "Ошибка", "Не удалось открыть предпросмотр")
