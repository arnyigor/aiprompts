import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set
from uuid import uuid4
import re

import pandas as pd

from src.prompt_manager import PromptManager


class ExcelPromptImporter:
    """Класс для импорта промптов из Excel файлов"""

    def __init__(self, income_dir: str = "income", prompts_dir: str = "../prompts"):
        """
        Инициализация импортера промптов
        
        Args:
            income_dir (str): Директория с входящими Excel файлами
            prompts_dir (str): Директория с промптами
        """
        self.logger = logging.getLogger(__name__)
        self.income_dir = Path(income_dir)
        self.prompts_dir = Path(prompts_dir)
        self.prompt_manager = PromptManager(str(self.prompts_dir))

        # Создаем директории, если они не существуют
        self.income_dir.mkdir(exist_ok=True)
        (self.income_dir / "processed").mkdir(exist_ok=True)
        self.prompts_dir.mkdir(exist_ok=True)

        # Получаем существующие категории и теги
        self.existing_categories = self._get_existing_categories()
        self.existing_tags = self._get_existing_tags()
        self.logger.info(f"Доступные категории: {', '.join(self.existing_categories)}")
        self.logger.info(f"Доступные теги: {', '.join(self.existing_tags)}")

    def _get_existing_categories(self) -> Set[str]:
        """Получает список существующих категорий"""
        return {
            'general',        # Общее
            'marketing',      # Маркетинг
            'technology',     # Технологии
            'creative',       # Творчество
            'business',       # Бизнес
            'education',      # Образование
            'healthcare',     # Здравоохранение
            'legal',         # Юридическое
            'entertainment', # Развлечения
            'common_tasks',  # Общие задачи
            'science',       # Наука
            'model_specific', # Специфичные модели
            'environment'    # Окружающая среда
        }

    def _get_existing_tags(self) -> Set[str]:
        """Получает список существующих тегов"""
        # Предопределенные теги
        predefined_tags = {
            'social', 'content', 'marketing', 'business', 'creative',
            'technology', 'education', 'writing', 'translation',
            'analysis', 'automation', 'development', 'ai', 'ml',
            'data', 'design', 'research', 'productivity'
        }

        # Получаем теги из существующих промптов
        existing_tags = set()
        for prompt in self.prompt_manager.list_prompts():
            if hasattr(prompt, 'tags'):
                existing_tags.update(prompt.tags)

        # Объединяем предопределенные и существующие теги
        all_tags = predefined_tags.union(existing_tags)
        self.logger.debug(
            f"Доступные теги: предопределенные ({len(predefined_tags)}), существующие ({len(existing_tags)}), всего уникальных ({len(all_tags)})")
        return all_tags

    def _validate_category(self, category: str) -> str:
        """Проверяет и возвращает валидную категорию"""
        if not category or category not in self.existing_categories:
            self.logger.warning(f"Категория '{category}' не существует. Используется 'general'")
            return 'general'
        return category

    def _validate_tags(self, tags: List[str]) -> List[str]:
        """Проверяет и возвращает только существующие теги"""
        valid_tags = [tag for tag in tags if tag in self.existing_tags]
        if len(valid_tags) < len(tags):
            invalid_tags = set(tags) - set(valid_tags)
            self.logger.warning(f"Пропущены несуществующие теги: {', '.join(invalid_tags)}")
        return valid_tags

    def _extract_category_from_description(self, description: str) -> str:
        """
        Извлекает категорию из описания промпта
        
        Args:
            description (str): Описание промпта
            
        Returns:
            str: Код категории
        """
        # Анализируем текст для определения категории
        text_lower = description.lower()
        
        # Определяем категорию по содержимому
        if any(word in text_lower for word in [
            'маркетинг', 'marketing', 'seo', 'продвижение', 'реклама', 'smm', 'контент',
            'продажи', 'email', 'social media', 'соцсети', 'пост', 'instagram', 'facebook'
        ]):
            return 'marketing'
            
        if any(word in text_lower for word in [
            'технолог', 'technology', 'programming', 'код', 'разработка', 'software',
            'hardware', 'ai', 'ml', 'database', 'данные', 'artificial intelligence',
            'machine learning', 'нейронные сети', 'neural network'
        ]):
            return 'technology'
            
        if any(word in text_lower for word in [
            'творчес', 'creative', 'дизайн', 'art', 'музыка', 'writing', 'контент',
            'написать', 'текст', 'статья', 'копирайтинг', 'copywriting'
        ]):
            return 'creative'
            
        if any(word in text_lower for word in [
            'бизнес', 'business', 'finance', 'management', 'startup',
            'предприниматель', 'продажи', 'sales', 'strategy', 'стратегия'
        ]):
            return 'business'
            
        if any(word in text_lower for word in [
            'образован', 'education', 'обучение', 'teaching', 'курс',
            'study', 'learn', 'учеба', 'преподавание', 'школа', 'университет'
        ]):
            return 'education'
            
        if any(word in text_lower for word in [
            'здоровье', 'health', 'medical', 'medicine', 'wellness',
            'больница', 'врач', 'doctor', 'patient', 'пациент'
        ]):
            return 'healthcare'
            
        if any(word in text_lower for word in [
            'юридическ', 'legal', 'law', 'право', 'закон',
            'contract', 'договор', 'суд', 'court', 'attorney'
        ]):
            return 'legal'
            
        if any(word in text_lower for word in [
            'развлечен', 'entertainment', 'game', 'игры', 'fun',
            'досуг', 'отдых', 'leisure', 'hobby', 'хобби'
        ]):
            return 'entertainment'
            
        if any(word in text_lower for word in [
            'task', 'задача', 'routine', 'daily', 'ежедневный',
            'повседневный', 'regular', 'регулярный', 'common', 'общий'
        ]):
            return 'common_tasks'
            
        if any(word in text_lower for word in [
            'наука', 'science', 'research', 'исследован', 'scientific',
            'научный', 'experiment', 'эксперимент', 'study', 'изучение'
        ]):
            return 'science'
            
        if any(word in text_lower for word in [
            'gpt', 'llm', 'chatgpt', 'model', 'prompt', 'промпт',
            'language model', 'языковая модель', 'ai model', 'chat'
        ]):
            return 'model_specific'
            
        if any(word in text_lower for word in [
            'экология', 'environment', 'nature', 'climate', 'природа',
            'climate change', 'изменение климата', 'eco', 'эко', 'green'
        ]):
            return 'environment'

        # Анализируем контент для определения категории
        if any(word in text_lower for word in ['write', 'написать', 'текст', 'статья']):
            return 'creative'
            
        if any(word in text_lower for word in ['prompt', 'промпт', 'gpt', 'chatgpt']):
            return 'model_specific'
            
        if any(word in text_lower for word in ['пост', 'social', 'соцсет']):
            return 'marketing'

        self.logger.debug(f"Не удалось определить категорию из описания: {description}")
        return 'general'

    def _extract_variables(self, ru_text: str, en_text: str) -> List[Dict]:
        """
        Извлекает переменные из текста и преобразует их в нужный формат
        
        Args:
            ru_text (str): Текст на русском
            en_text (str): Текст на английском
            
        Returns:
            List[Dict] или None: Список переменных в формате для модели Prompt или None, если переменные не найдены
        """
        # Извлекаем переменные из текста (в квадратных скобках)
        ru_vars = set(re.findall(r'\[(.*?)\]', ru_text))
        en_vars = set(re.findall(r'\[(.*?)\]', en_text))
        
        # Если переменные не найдены, возвращаем None
        if not ru_vars and not en_vars:
            return None
            
        # Создаем словари для каждой переменной
        variables = []
        for var_ru, var_en in zip(ru_vars, en_vars):
            variable = {
                'name': var_en.lower().replace('/', '_').replace(' ', '_'),  # нормализуем имя переменной
                'description': f"{var_ru} / {var_en}",  # объединяем описания через разделитель
                'type': 'string',  # по умолчанию все переменные строковые
                'required': True
            }
            variables.append(variable)
            
        # Если количество переменных не совпадает, добавляем оставшиеся
        remaining_ru = list(ru_vars)[len(en_vars):]
        for var_ru in remaining_ru:
            variable = {
                'name': var_ru.lower().replace('/', '_').replace(' ', '_'),
                'description': var_ru,  # используем только русское описание
                'type': 'string',
                'required': True
            }
            variables.append(variable)
            
        remaining_en = list(en_vars)[len(ru_vars):]
        for var_en in remaining_en:
            variable = {
                'name': var_en.lower().replace('/', '_').replace(' ', '_'),
                'description': var_en,  # используем только английское описание
                'type': 'string',
                'required': True
            }
            variables.append(variable)
            
        return variables if variables else None

    def read_excel_prompts(self, file_path: Path) -> List[Dict]:
        """
        Читает промпты из Excel файла
        
        Args:
            file_path (Path): Путь к Excel файлу
            
        Returns:
            List[Dict]: Список промптов с метаданными
        """
        try:
            # Читаем Excel файл
            df = pd.read_excel(file_path)
            self.logger.info(f"Прочитан файл {file_path}")
            self.logger.info(f"Размер файла: {len(df)} строк")
            self.logger.info(f"Доступные колонки: {', '.join(df.columns)}")
            
            # Выводим первые несколько строк для отладки
            self.logger.debug("Первые 5 строк файла:")
            for idx, row in df.head().iterrows():
                self.logger.debug(f"Строка {idx}:")
                for col in df.columns:
                    self.logger.debug(f"  {col}: {row[col]}")

            # Ищем колонки с русским и английским текстом
            ru_col = None
            en_col = None
            
            # Проверяем разные варианты названий колонок
            possible_ru_names = [
                'Русский', 'RU', 'Russian', 'Промпт', 'Текст',
                'Промты', 'Промты для соцсетей', 'Промпты'
            ]
            possible_en_names = [
                'Английский', 'EN', 'English', 'Prompt', 'Text',
                'Unnamed: 1', 'Translation', 'Перевод'
            ]
            
            # Сначала ищем точные совпадения
            for col in df.columns:
                col_str = str(col).strip()
                if col_str in possible_ru_names:
                    ru_col = col
                    self.logger.info(f"Найдена колонка с русским текстом (точное совпадение): {col}")
                elif col_str in possible_en_names:
                    en_col = col
                    self.logger.info(f"Найдена колонка с английским текстом (точное совпадение): {col}")
            
            # Если точных совпадений нет, ищем частичные
            if not (ru_col and en_col):
                for col in df.columns:
                    col_str = str(col).strip().lower()
                    if not ru_col and any(name.lower() in col_str for name in possible_ru_names):
                        ru_col = col
                        self.logger.info(f"Найдена колонка с русским текстом (частичное совпадение): {col}")
                    elif not en_col and any(name.lower() in col_str for name in possible_en_names):
                        en_col = col
                        self.logger.info(f"Найдена колонка с английским текстом (частичное совпадение): {col}")

            # Если все еще не нашли колонки, пробуем определить по содержимому
            if not (ru_col and en_col) and len(df.columns) >= 2:
                # Берем первые две колонки
                first_col = df.columns[0]
                second_col = df.columns[1]
                
                # Проверяем первые несколько строк на наличие русского/английского текста
                ru_score_first = 0
                en_score_first = 0
                ru_score_second = 0
                en_score_second = 0
                
                for _, row in df.head().iterrows():
                    text1 = str(row[first_col]).strip()
                    text2 = str(row[second_col]).strip()
                    
                    # Простая эвристика: подсчет кириллических символов
                    ru_score_first += sum(1 for c in text1 if '\u0400' <= c <= '\u04FF')
                    ru_score_second += sum(1 for c in text2 if '\u0400' <= c <= '\u04FF')
                    
                    # Подсчет латинских символов
                    en_score_first += sum(1 for c in text1 if 'a' <= c.lower() <= 'z')
                    en_score_second += sum(1 for c in text2 if 'a' <= c.lower() <= 'z')
                
                if not (ru_col and en_col):
                    if ru_score_first > en_score_first and en_score_second > ru_score_second:
                        ru_col = first_col
                        en_col = second_col
                        self.logger.info("Колонки определены по содержимому: первая - русский, вторая - английский")
                    elif en_score_first > ru_score_first and ru_score_second > en_score_second:
                        ru_col = second_col
                        en_col = first_col
                        self.logger.info("Колонки определены по содержимому: первая - английский, вторая - русский")

            if not (ru_col and en_col):
                self.logger.error(f"Не найдены колонки с текстом. Доступные колонки: {', '.join(df.columns)}")
                return []

            # Получаем описание категории из первой строки первой колонки
            first_cell = str(df.iloc[0, 0]) if not pd.isna(df.iloc[0, 0]) else ""
            category_description = first_cell.strip()
            
            if category_description:
                self.logger.info(f"Найдено описание категории: {category_description}")
                category = self._extract_category_from_description(category_description)
            else:
                category = 'general'
                self.logger.warning("Описание категории не найдено, используется 'general'")

            prompts = []
            # Начинаем с первой строки, если нет описания категории
            start_idx = 1 if not category_description else 2
            
            for idx, row in df.iloc[start_idx:].iterrows():
                try:
                    ru_text = str(row[ru_col]).strip() if not pd.isna(row[ru_col]) else ""
                    en_text = str(row[en_col]).strip() if not pd.isna(row[en_col]) else ""

                    if not ru_text or not en_text:
                        self.logger.warning(f"Пропущена строка {idx + 1}: пустые значения")
                        continue

                    # Определяем категорию на основе описания и содержимого
                    prompt_category = self._extract_category_from_description(ru_text)
                    if prompt_category == 'general':
                        # Если категория не определена из текста промпта, пробуем определить из описания
                        prompt_category = self._extract_category_from_description(category_description)
                    
                    # Определяем теги на основе контента
                    content_tags = self._extract_tags_from_content(ru_text, en_text)
                    suggested_tags = self._validate_tags(content_tags)
                    
                    # Если теги не определились, добавляем дефолтный тег
                    if not suggested_tags:
                        suggested_tags = ['general']
                        self.logger.debug(f"Для промпта добавлен дефолтный тег 'general'")

                    # Извлекаем переменные в правильном формате
                    variables = self._extract_variables(ru_text, en_text)
                    
                    # Определяем совместимые модели
                    compatible_models = self._get_compatible_models(ru_text, en_text, prompt_category)

                    # Создаем промпт с двумя языковыми версиями
                    prompt_data = {
                        'id': str(uuid4()),
                        'title': ru_text[:70] + ('...' if len(ru_text) > 70 else ''),  # Берем первые 70 символов русского текста
                        'content': {
                            'ru': ru_text,
                            'en': en_text
                        },
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow(),
                        'category': self._validate_category(prompt_category),
                        'tags': suggested_tags,
                        'description': category_description if category_description else f"Bilingual prompt {idx + 1}",
                        'variables': variables if variables else [],
                        'compatible_models': compatible_models  # Добавляем список совместимых моделей
                    }

                    self.logger.debug(
                        f"Создан промпт: {prompt_data['title']}\n"
                        f"Категория: {prompt_data['category']}\n"
                        f"Теги: {', '.join(prompt_data['tags'])}\n"
                        f"Совместимые модели: {', '.join(compatible_models)}\n"
                        f"Переменные: {', '.join(v['name'] for v in variables) if variables else 'нет'}"
                    )
                    prompts.append(prompt_data)

                except Exception as e:
                    self.logger.error(f"Ошибка при обработке строки {idx + 1}: {str(e)}", exc_info=True)
                    continue

            self.logger.info(f"Успешно прочитано {len(prompts)} промптов из файла")
            return prompts

        except Exception as e:
            self.logger.error(f"Ошибка при чтении файла {file_path}: {str(e)}", exc_info=True)
            return []

    def _extract_tags_from_content(self, ru_text: str, en_text: str) -> List[str]:
        """
        Извлекает теги из контента промпта
        
        Args:
            ru_text (str): Текст на русском
            en_text (str): Текст на английском
            
        Returns:
            List[str]: Список тегов
        """
        tags = set()
        text_lower = f"{ru_text.lower()} {en_text.lower()}"
        
        # Используем только предопределенные теги
        tag_keywords = {
            'social': ['social', 'соцсети', 'instagram', 'facebook', 'twitter', 'linkedin'],
            'content': ['content', 'контент', 'статья', 'пост', 'текст'],
            'marketing': ['marketing', 'маркетинг', 'реклама', 'продвижение', 'seo'],
            'business': ['business', 'бизнес', 'предприниматель', 'company', 'компания'],
            'creative': ['creative', 'творческий', 'креатив', 'art', 'искусство'],
            'technology': ['technology', 'технологии', 'tech', 'software', 'hardware'],
            'education': ['education', 'образование', 'обучение', 'teaching'],
            'writing': ['writing', 'копирайтинг', 'текст', 'статья', 'пост'],
            'translation': ['translation', 'перевод', 'translate', 'переводить'],
            'analysis': ['analysis', 'анализ', 'research', 'исследование'],
            'automation': ['automation', 'автоматизация', 'automate'],
            'development': ['development', 'разработка', 'programming', 'coding'],
            'ai': ['ai', 'artificial intelligence', 'искусственный интеллект'],
            'ml': ['ml', 'machine learning', 'машинное обучение'],
            'data': ['data', 'данные', 'database', 'база данных'],
            'design': ['design', 'дизайн', 'graphic', 'ui/ux'],
            'research': ['research', 'исследование', 'изучение', 'study'],
            'productivity': ['productivity', 'продуктивность', 'efficiency', 'эффективность'],
            'science': ['science', 'наука', 'scientific', 'научный', 'biology', 'биология', 'chemistry', 'химия', 'physics', 'физика'],
            'biology': ['biology', 'биология', 'клетка', 'cell', 'организм', 'organism', 'днк', 'dna', 'ген', 'gene',
                       'фотосинтез', 'photosynthesis', 'эволюция', 'evolution', 'экосистема', 'ecosystem',
                       'адаптация', 'adaptation', 'нервная система', 'nervous system']
        }
        
        # Добавляем теги на основе ключевых слов
        for tag, keywords in tag_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                tags.add(tag)
                
        return list(tags)

    def process_income_files(self) -> int:
        """
        Обрабатывает все Excel файлы в директории income
        
        Returns:
            int: Количество успешно обработанных промптов
        """
        processed_count = 0
        all_prompts = []  # Список для хранения всех прочитанных промптов
        processed_files = []  # Список успешно обработанных файлов

        try:
            # Получаем список Excel файлов
            excel_files = list(self.income_dir.glob("*.xlsx"))

            if not excel_files:
                self.logger.warning(f"Excel файлы не найдены в директории {self.income_dir}")
                return 0

            self.logger.info(f"Найдено файлов для обработки: {len(excel_files)}")

            # Сначала читаем все файлы и собираем промпты
            for file_path in excel_files:
                self.logger.info(f"Чтение файла {file_path}")

                # Читаем промпты из файла
                file_prompts = self.read_excel_prompts(file_path)

                if not file_prompts:
                    self.logger.warning(f"Файл {file_path} не содержит валидных промптов")
                    continue

                # Добавляем информацию о файле-источнике к каждому промпту
                for prompt in file_prompts:
                    prompt['source_file'] = str(file_path)

                all_prompts.extend(file_prompts)
                processed_files.append(file_path)
                self.logger.info(f"Прочитано {len(file_prompts)} промптов из файла {file_path.name}")

            # Выводим подробную статистику
            self.logger.info("\n=== Статистика импорта ===")
            self.logger.info(f"Всего найдено промптов: {len(all_prompts)}")
            self.logger.info(f"Файлы для обработки: {', '.join(f.name for f in processed_files)}")
            
            # Анализируем категории
            categories = {}
            for prompt in all_prompts:
                cat = prompt['category']
                if cat not in categories:
                    categories[cat] = 0
                categories[cat] += 1

            # Сортируем категории по количеству промптов
            sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
            total_prompts = len(all_prompts)

            self.logger.info("\nРаспределение по категориям:")
            for cat, count in sorted_categories:
                percentage = (count / total_prompts) * 100
                self.logger.info(f"- {cat:<15} {count:>4} промптов ({percentage:>5.1f}%)")

            # Анализируем теги
            tags = {}
            for prompt in all_prompts:
                for tag in prompt['tags']:
                    if tag not in tags:
                        tags[tag] = 0
                    tags[tag] += 1

            # Сортируем теги по количеству использований
            sorted_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)

            self.logger.info("\nИспользуемые теги (топ 10):")
            for tag, count in sorted_tags[:10]:
                percentage = (count / total_prompts) * 100
                self.logger.info(f"- {tag:<15} {count:>4} промптов ({percentage:>5.1f}%)")

            if len(sorted_tags) > 10:
                self.logger.info(f"\nОстальные теги ({len(sorted_tags) - 10}):")
                for tag, count in sorted_tags[10:]:
                    percentage = (count / total_prompts) * 100
                    self.logger.info(f"- {tag:<15} {count:>4} промптов ({percentage:>5.1f}%)")

            # Запрашиваем подтверждение
            self.logger.info("\nПожалуйста, проверьте данные перед сохранением.")
            confirmation = input("Введите 'yes' для подтверждения сохранения: ").strip().lower()
            
            if confirmation != 'yes':
                self.logger.info("Сохранение отменено пользователем")
                return 0

            # После подтверждения сохраняем промпты
            successful_prompts = 0
            for prompt_data in all_prompts:
                try:
                    self.prompt_manager.add_prompt(prompt_data)
                    successful_prompts += 1
                    processed_count += 1
                except Exception as e:
                    self.logger.error(
                        f"Ошибка при добавлении промпта {prompt_data.get('title', 'Unknown')}: {str(e)}",
                        exc_info=True
                    )
                    continue

            # После успешного сохранения перемещаем файлы в архив только если все промпты сохранены успешно
            if successful_prompts == len(all_prompts):
                for file_path in processed_files:
                    try:
                        processed_dir = self.income_dir / "processed"
                        new_path = processed_dir / f"{file_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        file_path.rename(new_path)
                        self.logger.info(f"Файл {file_path.name} перемещен в архив как {new_path.name}")
                    except Exception as e:
                        self.logger.error(f"Ошибка при перемещении файла {file_path}: {str(e)}")
            else:
                self.logger.warning(
                    f"Файлы оставлены в директории income, так как не все промпты были успешно сохранены "
                    f"({successful_prompts} из {len(all_prompts)})"
                )

            self.logger.info(f"\nИтоги обработки:")
            self.logger.info(f"Успешно сохранено {successful_prompts} из {len(all_prompts)} промптов")
            return processed_count

        except Exception as e:
            self.logger.error(f"Ошибка при обработке файлов: {str(e)}", exc_info=True)
            return processed_count

    def _get_compatible_models(self, ru_text: str, en_text: str, category: str) -> List[str]:
        """
        Определяет совместимые модели на основе содержимого промпта и его категории
        
        Args:
            ru_text (str): Текст промпта на русском
            en_text (str): Текст промпта на английском
            category (str): Категория промпта
            
        Returns:
            List[str]: Список совместимых моделей
        """
        text_lower = f"{ru_text.lower()} {en_text.lower()}"
        models = set()

        # Словарь категорий моделей и их возможностей
        model_categories = {
            'text_generation': {
                'keywords': ['написать', 'создать текст', 'придумать', 'сгенерировать текст', 
                           'write', 'create text', 'generate text', 'compose'],
                'models': ['GPT-4', 'GPT-3.5', 'Claude-3', 'Claude-2', 'Gemini-Pro']
            },
            'image_generation': {
                'keywords': ['картинк', 'изображени', 'нарисуй', 'визуализируй', 
                           'image', 'picture', 'draw', 'visualize', 'photo'],
                'models': ['Midjourney', 'DALL-E-3', 'Stable Diffusion']
            },
            'code_generation': {
                'keywords': ['код', 'программ', 'разработ', 'code', 'program', 'develop', 
                           'function', 'class', 'algorithm'],
                'models': ['GPT-4', 'Claude-3', 'Copilot', 'Code Llama']
            },
            'analysis': {
                'keywords': ['анализ', 'исследование', 'изучи', 'сравни', 
                           'analyze', 'research', 'study', 'compare'],
                'models': ['GPT-4', 'Claude-3', 'Gemini-Pro', 'Claude-2']
            },
            'translation': {
                'keywords': ['перевод', 'переведи', 'translate', 'translation'],
                'models': ['GPT-4', 'Claude-3', 'DeepL', 'Google Translate']
            }
        }

        # Определяем базовые модели на основе категории
        category_model_mapping = {
            'marketing': ['GPT-4', 'Claude-3', 'Gemini-Pro'],
            'technology': ['GPT-4', 'Claude-3', 'Code Llama', 'Copilot'],
            'creative': ['GPT-4', 'Claude-3', 'Midjourney', 'DALL-E-3'],
            'business': ['GPT-4', 'Claude-3', 'Claude-2'],
            'education': ['GPT-4', 'Claude-3', 'Gemini-Pro'],
            'healthcare': ['GPT-4', 'Claude-3'],
            'legal': ['GPT-4', 'Claude-3'],
            'entertainment': ['GPT-4', 'Claude-3', 'Midjourney'],
            'science': ['GPT-4', 'Claude-3', 'Gemini-Pro'],
            'model_specific': ['GPT-4', 'Claude-3'],
            'environment': ['GPT-4', 'Claude-3', 'Gemini-Pro']
        }

        # Добавляем базовые модели для категории
        if category in category_model_mapping:
            models.update(category_model_mapping[category])

        # Анализируем текст на наличие ключевых слов для определения дополнительных моделей
        for cat, data in model_categories.items():
            if any(keyword in text_lower for keyword in data['keywords']):
                models.update(data['models'])

        # Если не определили ни одной модели, добавляем базовые
        if not models:
            models.update(['GPT-4', 'Claude-3'])

        return sorted(list(models))
