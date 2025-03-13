from collections import defaultdict, Counter
from typing import Dict, List, Optional

from src.models import Category

CATEGORIES = {
    "general": {
        "name": {"ru": "Общее", "en": "General"},
        "parent": None,
        "children": [
            "common_tasks", "education", "entertainment", "legal", "healthcare"
        ]
    },
    "marketing": {
        "name": {"ru": "Маркетинг", "en": "Marketing"},
        "parent": "general",
        "children": [
            "social_media", "seo", "content_marketing", "advertising", "branding"
        ]
    },
    "technology": {
        "name": {"ru": "Технологии", "en": "Technology"},
        "parent": "general",
        "children": [
            "software", "data_science", "ai_ml", "cloud", "cybersecurity"
        ]
    },
    "creative": {
        "name": {"ru": "Творчество", "en": "Creative"},
        "parent": "general",
        "children": [
            "design", "writing", "art", "music", "video"
        ]
    },
    "business": {
        "name": {"ru": "Бизнес", "en": "Business"},
        "parent": "general",
        "children": [
            "finance", "hr", "project_management", "sales", "customer_service"
        ]
    },
    "education": {
        "name": {"ru": "Образование", "en": "Education"},
        "parent": "general",
        "children": [
            "courses", "research", "language_learning", "testing"
        ]
    },
    "healthcare": {
        "name": {"ru": "Здравоохранение", "en": "Healthcare"},
        "parent": "general",
        "children": [
            "diagnostics", "patient_care", "medical_research"
        ]
    },
    "legal": {
        "name": {"ru": "Юридическое", "en": "Legal"},
        "parent": "general",
        "children": ["contracts", "regulations", "dispute_resolution"]
    },
    "entertainment": {
        "name": {"ru": "Развлечения", "en": "Entertainment"},
        "parent": "general",
        "children": [
            "games", "music", "movies", "books"
        ]
    },
    "social_media": {
        "name": {"ru": "Соцсети", "en": "Social Media"},
        "parent": "marketing",
        "children": ["instagram", "facebook", "tiktok"]
    },
    "seo": {
        "name": {"ru": "SEO", "en": "SEO"},
        "parent": "marketing",
        "children": ["keyword_optimization", "content_strategy"]
    },
    "ai_ml": {
        "name": {"ru": "ИИ и ML", "en": "AI/ML"},
        "parent": "technology",
        "children": ["nlp", "computer_vision", "reinforcement_learning"]
    },
    "software": {
        "name": {"ru": "Программное обеспечение", "en": "Software"},
        "parent": "technology",
        "children": ["dev_ops", "web_dev", "mobile_dev"]
    },
    "design": {
        "name": {"ru": "Дизайн", "en": "Design"},
        "parent": "creative",
        "children": ["uiux", "graphic_design", "3d_modeling"]
    },
    "writing": {
        "name": {"ru": "Письмо", "en": "Writing"},
        "parent": "creative",
        "children": ["fiction", "academic", "technical"]
    },
    "finance": {
        "name": {"ru": "Финансы", "en": "Finance"},
        "parent": "business",
        "children": ["investment", "accounting", "risk_management"]
    },
    "hr": {
        "name": {"ru": "HR", "en": "HR"},
        "parent": "business",
        "children": ["recruitment", "training", "performance"]
    },
    "diagnostics": {
        "name": {"ru": "Диагностика", "en": "Diagnostics"},
        "parent": "healthcare",
        "children": ["medical_imaging", "symptom_analysis"]
    },
    "courses": {
        "name": {"ru": "Курсы", "en": "Courses"},
        "parent": "education",
        "children": ["programming", "mathematics", "languages"]
    },
    "games": {
        "name": {"ru": "Игры", "en": "Games"},
        "parent": "entertainment",
        "children": ["strategy", "puzzle", "casual"]
    },
    "music": {
        "name": {"ru": "Музыка", "en": "Music"},
        "parent": "entertainment",
        "children": ["composition", "production", "analysis"]
    },
    "common_tasks": {
        "name": {"ru": "Общие задачи", "en": "Common Tasks"},
        "parent": "general",
        "children": ["productivity", "translations", "automation"]
    },
    "science": {
        "name": {"ru": "Наука", "en": "Science"},
        "parent": "general",
        "children": ["physics", "chemistry", "biology"]
    },
    "model_specific": {
        "name": {"ru": "Специфичные модели", "en": "Model-Specific"},
        "parent": "general",
        "children": ["gpt-4", "dalle", "stable_diffusion", "midjourney"]
    },
    "programming": {
        "name": {"ru": "Программирование", "en": "Programming"},
        "parent": "technology",
        "children": ["python", "javascript", "data_structures"]
    },
    "data_analysis": {
        "name": {"ru": "Анализ данных", "en": "Data Analysis"},
        "parent": "technology",
        "children": ["statistics", "big_data", "visualization"]
    },
    "environment": {
        "name": {"ru": "Окружающая среда", "en": "Environment"},
        "parent": "general",
        "children": ["climate", "energy", "conservation"]
    },
    "game_dev": {
        "name": {"ru": "Разработка игр", "en": "Game Development"},
        "parent": "creative",
        "children": ["game_design", "asset_creation", "level_design"]
    }
}

KEYWORDS = {
    "marketing": {
        "keywords": ["продажа", "реклама", "target audience"],
        "children": {
            "social_media": ["инстаграм", "теги", "лайки"],
            "seo": ["seo", "ranking", "organic traffic"],
            "email_marketing": ["рассылка", "открытие письма", "CTR"]
        },
        "weight": 1.0
    },
    "technology": {
        "keywords": ["программирование", "апи", "база данных"],
        "children": {
            "ai_ml": ["нейросеть", "ml", "tensorflow"],
            "software": ["python", "javascript", "баг"],
            "cloud": ["aws", "azure", "виртуальный сервер"]
        },
        "weight": 1.0
    },
    "creative": {
        "keywords": ["дизайн", "арт", "фотошоп"],
        "children": {
            "graphic_design": ["типоографика", "вектор", "логотип"],
            "writing": ["сценарий", "стиль", "персонаж"],
            "music": ["композиция", "бэкграунд", "аудио"]
        },
        "weight": 1.0
    },
    "legal": {
        "keywords": ["договор", "закон", "суд"],
        "children": {
            "contracts": ["nda", "договор оферты", "арбитраж"],
            "regulations": ["gdpr", "покупка", "продажа"]
        },
        "weight": 1.0
    }
}

CONTEXT_RULES = {
    ("нейросеть", "обучение"): "ai_ml",
    ("инстаграм", "рассылка"): "social_media",
    ("договор", "арбитраж"): "contracts",
    ("логотип", "корпоративный"): "graphic_design"}

BLACKLIST = {
    "marketing": ["научный", "исследование"],
    "technology": ["музыка", "кино"]
}

def simple_russian_stemmer(word: str) -> str:
    """Простой стеммер для русского языка"""
    word = word.lower().strip()
    if len(word) <= 3:
        return word

    # Список популярных окончаний
    endings = [
        'ами', 'ями', 'ого', 'его', 'ому', 'ему',
        'ых', 'ий', 'ый', 'ой', 'ей', 'ай',
        'ть', 'еть', 'уть', 'ешь', 'нно',
        'ет', 'ют', 'ут', 'ат', 'ял',
        'ал', 'ла', 'на', 'ны', 'ть',
        'ем', 'им', 'ам', 'ом', 'ах',
        'ях', 'ую', 'ю', 'у', 'а',
        'я', 'о', 'е', 'ы', 'и'
    ]
    
    result = word
    for ending in endings:
        if len(result) > len(ending) + 2 and result.endswith(ending):
            result = result[:-len(ending)]
            break
    
    return result

def stem_text(text: str) -> str:
    """Стемминг текста"""
    return " ".join([simple_russian_stemmer(word) for word in text.split()])

class CategoryManager:
    """
        Пример добавления новой категории:

        CATEGORIES["natural_language"] = {
            "name": {"ru": "Естественный язык", "en": "Natural Language"},
            "parent": "ai",
            "children": []
        }
        """

    def __init__(self):
        self.keywords = KEYWORDS
        self.context_rules = CONTEXT_RULES
        self.blacklist = BLACKLIST
        self.categories = self.load_categories()

    def get_categories(self) -> dict:
        """Возвращает словарь всех категорий с их локализованными названиями"""
        return CATEGORIES

    def load_categories(self) -> dict[str, Category]:
        return {
            code: Category(
                code=code,
                name=data["name"],
                parent=data["parent"],
                children=data["children"]
            )
            for code, data in CATEGORIES.items()
        }

    def get_category_tree(self) -> dict:
        """Возвращает дерево категорий в иерархическом виде"""
        tree = {}
        for code, category in CATEGORIES.items():
            if category["parent"] is None:  # Корневые категории
                tree[code] = self._build_subtree(code)
        return tree

    def _build_subtree(self, parent_code: str) -> dict:
        """Рекурсивно строит поддерево для заданной категории"""
        subtree = {
            "name": CATEGORIES[parent_code]["name"],
            "children": {}
        }

        for child_code in CATEGORIES[parent_code].get("children", []):
            if child_code in CATEGORIES:
                subtree["children"][child_code] = self._build_subtree(child_code)

        return subtree

    def get_category(self, code: str) -> Category:
        return self.categories.get(code)

    def get_localized_name(self, code: str, lang: str = "ru") -> str:
        category = self.get_category(code)
        return category.name.get(lang, code) if category else code

    def get_all_codes(self) -> list[str]:
        return list(self.categories.keys())

    def get_children(self, parent_code: str) -> list[str]:
        return self.categories[parent_code].children

    def suggest(self, text: str) -> List[str]:
        scores = defaultdict(float)
        stemmed_text = self._stem_text(text)
        word_counts = self._count_words(stemmed_text)

        # Базовый анализ ключевых слов
        self._analyze_base_keywords(word_counts, scores)

        # Анализ контекстных правил
        self._analyze_context_rules(text, scores)

        # Учет иерархии и родительских категорий
        self._apply_hierarchy_boost(scores)

        # Учет блэклиста
        self._apply_blacklist(text, scores)

        # Сортировка и фильтрация
        return self._sort_and_filter_scores(scores)

    def _stem_text(self, text: str) -> str:
        """Стемминг текста"""
        return stem_text(text)

    def _count_words(self, text: str) -> Dict[str, int]:
        """Подсчет частоты слов"""
        return Counter(text.split())

    def _analyze_base_keywords(self, word_counts, scores):
        """Анализ ключевых слов базовых категорий"""
        for category, data in self.keywords.items():
            category_weight = data.get("weight", 1.0)
            for word in data["keywords"]:
                stemmed_word = simple_russian_stemmer(word)
                if stemmed_word in word_counts:
                    scores[category] += category_weight * word_counts[stemmed_word]

    def _analyze_children(self, category: str, word_counts, scores):
        """Анализ подкатегорий"""
        children = self.keywords.get(category, {}).get("children", {})
        for child, child_keywords in children.items():
            child_weight = 1.5  # Подкатегории важнее
            for word in child_keywords:
                stemmed_word = simple_russian_stemmer(word)
                if stemmed_word in word_counts:
                    scores[child] += child_weight * word_counts[stemmed_word]
                    # Увеличиваем родительскую категорию
                    scores[category] += child_weight * 0.3 * word_counts[stemmed_word]

    def _analyze_context_rules(self, text: str, scores):
        """Анализ контекстных комбинаций"""
        for (word1, word2), category in self.context_rules.items():
            if word1.lower() in text and word2.lower() in text:
                scores[category] += 2.0  # Высокий вес за комбинацию

    def _apply_hierarchy_boost(self, scores):
        """Учет иерархии категорий"""
        for category in list(scores.keys()):
            parent = self._get_parent_category(category)
            while parent:
                scores[parent] += scores[category] * 0.5
                parent = self._get_parent_category(parent)

    def _get_parent_category(self, category: str) -> Optional[str]:
        """Поиск родительской категории (через структуру KEYWORDS)"""
        for parent, data in self.keywords.items():
            if category in data.get("children", {}):
                return parent
        return None

    def _apply_blacklist(self, text: str, scores):
        """Применение блэклиста"""
        for category in scores:
            forbidden_words = self.blacklist.get(category, [])
            for word in forbidden_words:
                if word in text.lower():
                    scores[category] *= 0.5

    def _sort_and_filter_scores(self, scores) -> List[str]:
        """Сортировка и фильтрация результатов"""
        sorted_scores = sorted(scores.items(), key=lambda x: (-x[1], len(x[0])))
        return [code for code, _ in sorted_scores if code in self.keywords][:5]
