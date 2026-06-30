"""Structured paper understanding produced before storyboard planning."""

from pydantic import BaseModel, Field


class EvidencePoint(BaseModel):
    """A concrete result or claim grounded in the paper."""

    claim: str = Field(min_length=1, description="What the paper shows or proves")
    detail: str = Field(
        min_length=1,
        description="Specific number, baseline comparison, or metric",
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
    evidence: list[EvidencePoint] = Field(
        min_length=1,
        max_length=8,
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
    evidence: list[EvidencePoint] = Field(min_length=1, max_length=8)
    limitations: str = Field(min_length=1)
    so_what: str = Field(min_length=1)
