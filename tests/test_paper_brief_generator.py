"""Unit tests for paper brief generation."""

import pytest
from app.models.paper_brief import PaperBriefResponse
from app.models.pipeline import ContentPlan
from app.models.section import Section
from app.services.paper_brief_generator import PaperBriefGenerationError, PaperBriefGenerator

from tests.test_stages import _sample_document


class _FakeGeminiClient:
    def __init__(self, response: PaperBriefResponse) -> None:
        self._response = response
        self.prompts: list[str] = []

    def generate_model(self, prompt: str, response_model):
        self.prompts.append(prompt)
        return self._response


def _sample_brief_response():
    from tests.conftest import sample_brief_response

    return sample_brief_response()


def _content_plan() -> ContentPlan:
    return ContentPlan(
        document=_sample_document(),
        selected_sections=[
            Section(
                id="sec-1",
                title="Results",
                content="Within 0.2 BLEU of the full model on WMT14.",
                page_numbers=[1],
                paragraph_indices=[1],
                importance_score=0.9,
            ),
        ],
    )


def test_generate_brief_returns_structured_model() -> None:
    fake_client = _FakeGeminiClient(_sample_brief_response())
    generator = PaperBriefGenerator(gemini_client=fake_client)

    brief = generator.generate_brief(_content_plan())

    assert brief.key_insight.startswith("A new attention")
    assert brief.evidence[0].detail.startswith("Within 0.2 BLEU")
    assert "Results" in fake_client.prompts[0]


def test_generate_brief_requires_api_key_when_client_not_injected() -> None:
    from app.config import Settings

    generator = PaperBriefGenerator(settings=Settings(gemini_api_key=None))

    with pytest.raises(PaperBriefGenerationError, match="GEMINI_API_KEY"):
        generator.generate_brief(_content_plan())
