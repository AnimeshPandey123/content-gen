"""Unit tests for section selection models."""

import pytest
from app.models.section_selection import RankedSection, SectionSelectionResponse
from pydantic import ValidationError


def test_ranked_section_importance_bounds() -> None:
    with pytest.raises(ValidationError):
        RankedSection(section="Results", importance=1.5)


def test_section_selection_response_limits() -> None:
    with pytest.raises(ValidationError):
        SectionSelectionResponse(sections=[])

    with pytest.raises(ValidationError):
        SectionSelectionResponse(
            sections=[RankedSection(section=f"S{i}", importance=0.5) for i in range(21)],
        )
