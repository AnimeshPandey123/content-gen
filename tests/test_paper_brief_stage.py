"""Unit tests for paper brief stage."""

from app.models.paper_brief import PaperBriefResponse
from app.models.pipeline import ContentPlan
from app.services.paper_brief_generator import PaperBriefGenerator
from app.services.stages.paper_brief import PaperBriefStage

from tests.test_paper_brief_generator import _content_plan
from tests.conftest import sample_brief_response


class _FakeGeminiClient:
    def generate_model(self, prompt, response_model):
        return sample_brief_response()


def test_paper_brief_stage_attaches_brief_to_content_plan() -> None:
    stage = PaperBriefStage(generator=PaperBriefGenerator(gemini_client=_FakeGeminiClient()))
    content_plan = _content_plan()

    result = stage.run(content_plan)

    assert isinstance(result, ContentPlan)
    assert result.paper_brief is not None
    assert result.paper_brief.mechanism.startswith("Queries attend")
