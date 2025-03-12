# data/models.py
from datetime import datetime
from typing import List, Dict, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field, validator, ConfigDict


class Category(BaseModel):
    code: str
    name: dict[str, str]
    parent: Optional[str] = None
    children: list[str] = []


class Variable(BaseModel):
    name: str
    type: str  # "string", "number", "list"
    description: str
    examples: List[str] = []

    @validator('type')
    def validate_type(cls, v):
        allowed_types = ['string', 'number', 'list']
        if v not in allowed_types:
            raise ValueError(f"Тип должен быть одним из: {allowed_types}")
        return v


class Prompt(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), description="UUID")
    title: str
    version: str = "1.0.0"
    status: str = "draft"
    is_local: bool = True
    is_favorite: bool = False
    description: str
    content: Union[str, Dict[str, str]] = Field(
        default_factory=lambda: {"ru": "", "en": ""},
        description="Контент в виде строки или словаря с поддержкой языков (ru/en)"
    )
    compatible_models: List[str] = []
    category: str = "general"
    tags: list[str] = []
    variables: List[Variable]
    metadata: Dict = {}
    rating: Dict[str, Union[float, int]] = Field(
        default_factory=lambda: {"score": 0.0, "votes": 0}
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        validate_default=True,  # Валидировать значения по умолчанию
        json_encoders={datetime: lambda v: v.isoformat()},
        strict=True
    )

    @validator('content')
    def check_content(cls, v):
        if isinstance(v, str):
            # Если передана строка, возвращаем её как есть
            return v
        elif isinstance(v, dict):
            # Если передан словарь, проверяем наличие хотя бы одной языковой версии
            if not v.get('ru') and not v.get('en'):
                raise ValueError("Контент должен содержать русскую или английскую версию")
            return v
        else:
            raise ValueError("Контент должен быть строкой или словарем")

    @validator('tags')
    def check_tags(cls, v):
        if not v:
            raise ValueError("Теги не могут быть пустыми")
        return v

    def model_post_init(self, __context) -> None:
        # Обновляем updated_at при изменении любых полей
        object.__setattr__(self, 'updated_at', datetime.utcnow())
