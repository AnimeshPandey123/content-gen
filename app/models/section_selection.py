"""LLM-ranked section selection models."""

from pydantic import BaseModel, Field


class RankedSection(BaseModel):
    """A section title ranked by the LLM for short-form video potential."""

    section: str = Field(min_length=1, description="Section title")
    importance: float = Field(ge=0.0, le=1.0)


class SectionSelectionResponse(BaseModel):
    """Structured Gemini response for section selection."""

    sections: list[RankedSection] = Field(
        min_length=1,
        max_length=5,
        description="Top interesting sections ordered by importance",
    )
