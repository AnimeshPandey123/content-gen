"""LLM-backed storyboard generation using Gemini."""

import re

from app.agents.gemini_client import GeminiClient, GeminiClientError
from app.config import Settings, get_settings
from app.models.pipeline import ContentPlan
from app.models.scene import Scene, SceneSource, SceneVisual
from app.models.section import Section
from app.models.storyboard import Storyboard
from app.models.storyboard_generation import PlannedScene, StoryboardGenerationResponse
from app.prompts.storyboard import build_storyboard_prompt
from app.services.screenshot_region_planner import ScreenshotRegionError, ScreenshotRegionPlanner


class StoryboardGenerationError(Exception):
    """Raised when storyboard generation cannot be completed."""


class StoryboardGenerator:
    """Plan storyboard structure with Gemini before script generation."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        gemini_client: GeminiClient | None = None,
        region_planner: ScreenshotRegionPlanner | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._gemini_client = gemini_client
        self._region_planner = region_planner or ScreenshotRegionPlanner(settings=self._settings)

    def generate_storyboard(self, content_plan: ContentPlan) -> Storyboard:
        planned_scenes = self._plan_scenes(content_plan)
        return self._build_storyboard(content_plan, planned_scenes)

    def plan_scenes(self, content_plan: ContentPlan) -> list[PlannedScene]:
        """Return raw LLM-planned scenes for the content plan."""
        return self._plan_scenes(content_plan)

    def _plan_scenes(self, content_plan: ContentPlan) -> list[PlannedScene]:
        max_scenes = min(
            self._settings.storyboard_max_scenes,
            len(content_plan.selected_sections) * 3,
        )
        prompt = build_storyboard_prompt(content_plan, max_scenes=max_scenes)
        client = self._gemini_client or self._build_client()

        try:
            response = client.generate_model(prompt, StoryboardGenerationResponse)
        except GeminiClientError as exc:
            raise StoryboardGenerationError(str(exc)) from exc

        return response.scenes[:max_scenes]

    def _build_client(self) -> GeminiClient:
        api_key = self._settings.gemini_api_key
        if not api_key:
            raise StoryboardGenerationError(
                "GEMINI_API_KEY is not configured for storyboard generation",
            )
        return GeminiClient(api_key=api_key, model=self._settings.gemini_model)

    def _build_storyboard(
        self,
        content_plan: ContentPlan,
        planned_scenes: list[PlannedScene],
    ) -> Storyboard:
        document = content_plan.document
        scenes: list[Scene] = []

        for index, planned in enumerate(planned_scenes, start=1):
            section = _match_section(content_plan.selected_sections, planned.source.section)
            if section is None:
                continue

            try:
                page_number, crop = self._region_planner.crop_for_paragraph(
                    document,
                    planned.source.paragraph,
                )
            except ScreenshotRegionError:
                continue

            scenes.append(
                Scene(
                    id=f"{document.id}-scene-{index}",
                    section_id=section.id,
                    order=index - 1,
                    goal=planned.goal,
                    duration_seconds=planned.duration_seconds,
                    source=SceneSource(
                        section=section.title,
                        page=planned.source.page,
                        paragraph=planned.source.paragraph,
                    ),
                    visual=SceneVisual(page=page_number, crop=crop),
                ),
            )

        if not scenes:
            raise StoryboardGenerationError("No scenes matched the LLM storyboard output")

        return Storyboard(document_id=document.id, scenes=scenes)


def _match_section(sections: list[Section], source_title: str) -> Section | None:
    normalized_target = _normalize_title(source_title)
    for section in sections:
        if _normalize_title(section.title) == normalized_target:
            return section

    for section in sections:
        normalized_section = _normalize_title(section.title)
        if normalized_target in normalized_section or normalized_section in normalized_target:
            return section

    return None


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().casefold())
