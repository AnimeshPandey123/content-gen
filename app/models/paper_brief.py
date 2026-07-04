"""Structured paper understanding produced before storyboard planning."""

from pydantic import BaseModel, Field


class EvidencePoint(BaseModel):
    """A concrete result or claim grounded in the paper."""

    claim: str = Field(min_length=1, description="What the paper shows or proves")
    detail: str = Field(
        min_length=1,
        description="Specific number, baseline comparison, or metric",
    )
    meaning: str = Field(
        min_length=1,
        description="What this result means for a tech-literate non-researcher",
    )
    source_section: str = Field(
        default="",
        description="Section title this evidence comes from",
    )


class PaperBrief(BaseModel):
    """Synthesized understanding of the paper for downstream LLM stages."""

    problem: str = Field(min_length=1, description="Problem or gap the paper addresses")
    key_insight: str = Field(
        min_length=1,
        description="Core idea in one plain-language sentence",
    )
    mechanism: str = Field(
        min_length=1,
        description="How the method or approach works, briefly",
    )
    intuition: str = Field(
        min_length=1,
        description="Everyday analogy or mental model that makes the core idea click",
    )
    evidence: list[EvidencePoint] = Field(
        min_length=1,
        max_length=12,
        description="Strongest evidence points with specifics",
    )
    limitations: str = Field(
        min_length=1,
        description="Main caveat, assumption, or limitation",
    )
    so_what: str = Field(
        min_length=1,
        description="Why this matters to a smart non-expert",
    )


class PaperBriefResponse(BaseModel):
    """Structured Gemini response for paper brief generation."""

    problem: str = Field(min_length=1)
    key_insight: str = Field(min_length=1)
    mechanism: str = Field(min_length=1)
    intuition: str = Field(min_length=1)
    evidence: list[EvidencePoint] = Field(min_length=1, max_length=12)
    limitations: str = Field(min_length=1)
    so_what: str = Field(min_length=1)
