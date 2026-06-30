"""LLM-backed paper brief generation using Gemini."""

from app.agents.gemini_client import GeminiClient, GeminiClientError
from app.config import Settings, get_settings
from app.models.paper_brief import PaperBrief, PaperBriefResponse
from app.models.pipeline import ContentPlan
from app.prompts.paper_brief import build_paper_brief_prompt


class PaperBriefGenerationError(Exception):
    """Raised when paper brief generation cannot be completed."""


class PaperBriefGenerator:
    """Synthesize structured paper understanding before storyboard planning."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        gemini_client: GeminiClient | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._gemini_client = gemini_client

    def generate_brief(self, content_plan: ContentPlan) -> PaperBrief:
        prompt = build_paper_brief_prompt(content_plan)
        client = self._gemini_client or self._build_client()

        try:
            response = client.generate_model(prompt, PaperBriefResponse)
        except GeminiClientError as exc:
            raise PaperBriefGenerationError(str(exc)) from exc

        return PaperBrief.model_validate(response.model_dump())

    def _build_client(self) -> GeminiClient:
        api_key = self._settings.gemini_api_key
        if not api_key:
            raise PaperBriefGenerationError(
                "GEMINI_API_KEY is not configured for paper brief generation",
            )
        return GeminiClient(api_key=api_key, model=self._settings.gemini_model)
