"""Unit tests for section selection prompts."""

from app.prompts.section_selection import build_section_selection_prompt
from app.services.document_sections import SectionCandidate


def test_build_section_selection_prompt_includes_candidates() -> None:
    prompt = build_section_selection_prompt(
        [
            SectionCandidate(title="Results", content="Accuracy was 95%."),
            SectionCandidate(title="Methods", content="We trained a model."),
        ],
        document_title="Sample Paper",
    )

    assert "Sample Paper" in prompt
    assert "Results" in prompt
    assert "Methods" in prompt
    assert '"importance": 0.95' in prompt
    assert "Decide how many" in prompt
    assert "Choose the top" not in prompt
    assert "tech-literate" in prompt.lower()
    assert "ablation" in prompt.lower()
    assert "conceptual story" in prompt
