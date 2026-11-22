import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class MaterialSection(BaseModel):
    id: str
    title: str
    text: str


class QuizQuestion(BaseModel):
    id: str
    section_id: str
    text: str
    options: list[str] = Field(min_length=2, max_length=6)
    correct_option: int = Field(ge=0)
    explanation: str

    @model_validator(mode="after")
    def validate_correct_option(self) -> "QuizQuestion":
        if self.correct_option >= len(self.options):
            raise ValueError("correct_option выходит за пределы options")
        return self


class TrainingMaterial(BaseModel):
    slug: str
    version: str
    title: str
    demo: bool
    summary: str
    sections: list[MaterialSection] = Field(min_length=1)
    questions: list[QuizQuestion] = Field(min_length=1)

    def section_title(self, section_id: str) -> str:
        for section in self.sections:
            if section.id == section_id:
                return section.title
        return "Раздел материала"

    def model_context(self) -> str:
        return "\n\n".join(f"[{s.id}] {s.title}\n{s.text}" for s in self.sections)


@dataclass(frozen=True)
class MaterialCatalog:
    materials: dict[str, TrainingMaterial]

    @classmethod
    def load(cls, directory: Path) -> "MaterialCatalog":
        loaded: dict[str, TrainingMaterial] = {}
        for path in sorted(directory.glob("*.json")):
            material = TrainingMaterial.model_validate(json.loads(path.read_text(encoding="utf-8")))
            if material.slug in loaded:
                raise ValueError(f"Повторяющийся slug материала: {material.slug}")
            loaded[material.slug] = material
        if not loaded:
            raise ValueError(f"В каталоге {directory} нет материалов")
        return cls(loaded)

    def get(self, slug: str) -> TrainingMaterial:
        try:
            return self.materials[slug]
        except KeyError as exc:
            raise ValueError("Материал не найден") from exc
