"""Unit tests for Gemini-backed section selection."""

import pytest
from app.models.blocks import Heading, Paragraph
from app.models.document import Document
from app.models.metadata import DocumentMetadata
from app.models.page import Page
from app.models.section_selection import RankedSection, SectionSelectionResponse
from app.services.document_sections import SectionCandidate
from app.services.section_selector import SectionSelectionError, SectionSelector, _match_candidate


class _FakeGeminiClient:
    def __init__(self, response: SectionSelectionResponse) -> None:
        self._response = response
        self.prompts: list[str] = []

    def generate_model(self, prompt: str, response_model):
        self.prompts.append(prompt)
        return self._response


def _document() -> Document:
    return Document(
        id="doc-1",
        source_path="/tmp/paper.pdf",
        title="Sample Paper",
        metadata=DocumentMetadata(page_count=1),
        pages=[
            Page(
                page_number=1,
                blocks=[
                    Heading(id="h1", order=0, text="Introduction", level=1),
                    Paragraph(id="p1", order=1, text="Intro body."),
                    Heading(id="h2", order=2, text="Results", level=1),
                    Paragraph(id="p2", order=3, text="We achieved 95% accuracy."),
                    Heading(id="h3", order=4, text="Methods", level=1),
                    Paragraph(id="p3", order=5, text="We trained a model."),
                ],
            ),
        ],
    )


def test_rank_sections_returns_llm_rankings() -> None:
    fake_client = _FakeGeminiClient(
        SectionSelectionResponse(
            sections=[
                RankedSection(section="Results", importance=0.95),
                RankedSection(section="Methods", importance=0.8),
            ],
        ),
    )
    selector = SectionSelector(gemini_client=fake_client)

    rankings = selector.rank_sections(_document())

    assert rankings[0].section == "Results"
    assert rankings[0].importance == 0.95
    assert "Results" in fake_client.prompts[0]


def test_select_sections_builds_section_models() -> None:
    fake_client = _FakeGeminiClient(
        SectionSelectionResponse(
            sections=[
                RankedSection(section="Results", importance=0.95),
                RankedSection(section="Introduction", importance=0.7),
            ],
        ),
    )
    selector = SectionSelector(gemini_client=fake_client)

    sections = selector.select_sections(_document())

    assert len(sections) == 2
    assert sections[0].title == "Results"
    assert sections[0].importance_score == 0.95
    assert sections[0].paragraph_indices == [2]
    assert sections[1].title == "Introduction"


def test_select_sections_requires_api_key_when_client_not_injected() -> None:
    from app.config import Settings

    selector = SectionSelector(settings=Settings(gemini_api_key=None))

    with pytest.raises(SectionSelectionError, match="GEMINI_API_KEY"):
        selector.select_sections(_document())


def test_rank_sections_wraps_gemini_errors() -> None:
    class _BadClient:
        def generate_model(self, prompt, response_model):
            from app.agents.gemini_client import GeminiClientError

            raise GeminiClientError("boom")

    selector = SectionSelector(gemini_client=_BadClient())

    with pytest.raises(SectionSelectionError, match="boom"):
        selector.rank_sections(_document())


def test_build_client_uses_settings_api_key(monkeypatch) -> None:
    from app.config import Settings

    created: list[str] = []

    class _RecordingClient:
        def __init__(self, *, api_key: str, model: str) -> None:
            created.append(api_key)

        def generate_model(self, prompt, response_model):
            return SectionSelectionResponse(
                sections=[RankedSection(section="Results", importance=0.9)],
            )

    monkeypatch.setattr(
        "app.services.section_selector.GeminiClient",
        lambda **kwargs: _RecordingClient(**kwargs),
    )
    selector = SectionSelector(settings=Settings(gemini_api_key="secret-key"))
    selector.rank_sections(_document())
    assert created == ["secret-key"]


def test_select_sections_raises_when_llm_returns_unknown_sections() -> None:
    fake_client = _FakeGeminiClient(
        SectionSelectionResponse(
            sections=[RankedSection(section="Conclusion", importance=0.9)],
        ),
    )
    selector = SectionSelector(gemini_client=fake_client)

    with pytest.raises(SectionSelectionError, match="No sections matched"):
        selector.select_sections(_document())


def test_match_candidate_supports_partial_title_match() -> None:
    candidates = [
        SectionCandidate(title="Results and Discussion", content="Body"),
    ]
    matched = _match_candidate(candidates, "Results")
    assert matched is not None
    assert matched.title == "Results and Discussion"
