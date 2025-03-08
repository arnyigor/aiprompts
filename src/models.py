# data/models.py
from datetime import datetime
from typing import List, Dict
from uuid import uuid4

from pydantic import BaseModel, Field, validator, ConfigDict


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
    description: str
    content: Dict[str, str] = Field(  # Контент на разных языках
        default_factory=lambda: {"ru": "", "en": ""},
        description="Контент с поддержкой языков (ru/en)"
    )
    category: str
    tags: List[str]
    variables: List[Variable]
    metadata: dict = {}
    ai_model: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        validate_default=True,  # Валидировать значения по умолчанию
        json_encoders={datetime: lambda v: v.isoformat()},
        strict=True
    )

    @validator('content')
    def check_content(cls, v):
        if not v.get('ru') and not v.get('en'):
            raise ValueError("Контент должен содержать русскую или английскую версию")
        return v

    @validator('tags')
    def check_tags(cls, v):
        if not v:
            raise ValueError("Теги не могут быть пустыми")
        return v

    def model_post_init(self, __context) -> None:
        # Обновляем updated_at при изменении любых полей
        object.__setattr__(self, 'updated_at', datetime.utcnow())
