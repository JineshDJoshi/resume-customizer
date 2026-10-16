"""Pydantic models describing the structured resume the LLM must return."""
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class Lenient(BaseModel):
    """Drops null values so a sloppy LLM response still validates."""

    @model_validator(mode="before")
    @classmethod
    def _drop_none(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if v is not None}
        return data


class SkillGroup(Lenient):
    category: str = ""
    items: list[str] = Field(default_factory=list)


class ExperienceItem(Lenient):
    title: str = ""
    company: str = ""
    location: str = ""
    dates: str = ""
    bullets: list[str] = Field(default_factory=list)


class ProjectItem(Lenient):
    name: str = ""
    bullets: list[str] = Field(default_factory=list)


class Resume(Lenient):
    name: str = ""
    contact: list[str] = Field(default_factory=list)
    summary: str = ""
    skills: list[SkillGroup] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)

    @field_validator("skills", mode="before")
    @classmethod
    def _skills_may_be_flat(cls, v: Any) -> Any:
        # Accept ["Python", "SQL"] as well as [{"category":..., "items":[...]}]
        if isinstance(v, list) and v and all(isinstance(i, str) for i in v):
            return [{"category": "Skills", "items": v}]
        return v


class Analysis(Lenient):
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    changes_summary: list[str] = Field(default_factory=list)


class LLMResult(Lenient):
    resume: Resume
    analysis: Analysis = Field(default_factory=Analysis)
