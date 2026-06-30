"""LLM-backed storyboard generation using Gemini."""

import re

from app.agents.gemini_client import GeminiClient, GeminiClientError
from app.config import Settings, get_settings
from app.models.document import Document
from app.models.pipeline import ContentPlan
from app.models.scene import Scene, SceneSource, SceneVisual
from app.models.section import Section
from app.models.storyboard import Storyboard
from app.models.storyboard_generation import (
    PlannedScene,
    StoryboardGenerationResponse,
)
from app.models.video_plan import VideoPlan
from app.prompts.storyboard import build_storyboard_prompt
from app.services.camera_planner import CameraPlanner
from app.services.duration_budget import fit_scene_durations
from app.services.screenshot_region_planner import ScreenshotRegionError, ScreenshotRegionPlanner
from app.services.timeline_builder import TimelineBuilder


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
        camera_planner: CameraPlanner | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._gemini_client = gemini_client
        self._region_planner = region_planner or ScreenshotRegionPlanner(settings=self._settings)
        self._camera_planner = camera_planner or CameraPlanner(
            settings=self._settings,
            region_planner=self._region_planner,
        )
        self._timeline_builder = TimelineBuilder()

    def generate_storyboard(self, content_plan: ContentPlan) -> Storyboard:
        planned_scenes, plan = self._plan_scenes(content_plan)
        return self._build_storyboard(content_plan, planned_scenes, plan)

    def plan_scenes(self, content_plan: ContentPlan) -> list[PlannedScene]:
        """Return raw LLM-planned scenes for the content plan."""
        planned_scenes, _plan = self._plan_scenes(content_plan)
        return planned_scenes

    def _plan_scenes(self, content_plan: ContentPlan) -> tuple[list[PlannedScene], VideoPlan]:
        prompt = build_storyboard_prompt(content_plan)
        client = self._gemini_client or self._build_client()

        try:
            response = client.generate_model(prompt, StoryboardGenerationResponse)
        except GeminiClientError as exc:
            raise StoryboardGenerationError(str(exc)) from exc

        return self._cap_planned_output(response)

    def _cap_planned_output(
        self,
        response: StoryboardGenerationResponse,
    ) -> tuple[list[PlannedScene], VideoPlan]:
        plan = response.plan.model_copy(
            update={
                "target_video_duration_seconds": min(
                    response.plan.target_video_duration_seconds,
                    self._settings.max_video_duration_seconds,
                ),
            },
        )
        scenes: list[PlannedScene] = []
        for scene in response.scenes[: self._settings.max_storyboard_scenes]:
            shots = scene.shots[: self._settings.max_shots_per_scene]
            scenes.append(scene.model_copy(update={"shots": shots}))
        return scenes, plan

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
        plan: VideoPlan,
    ) -> Storyboard:
        document = content_plan.document
        scenes: list[Scene] = []

        for index, planned in enumerate(planned_scenes, start=1):
            section = _match_section(content_plan.selected_sections, planned.source.section)
            if section is None:
                continue

            try:
                shots = self._camera_planner.resolve_shots(planned, document)
            except ScreenshotRegionError:
                continue

            first_shot = shots[0]
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
                    shots=shots,
                    visual=SceneVisual(page=first_shot.page, crop=first_shot.crop),
                ),
            )

        if not scenes:
            raise StoryboardGenerationError("No scenes matched the LLM storyboard output")

        fitted_scenes = self._fit_duration_budget(
            self._with_title_page_scene(document, content_plan, scenes, plan),
            plan,
        )
        video_timeline = self._timeline_builder.build_video_timeline(
            fitted_scenes,
            transition_duration_seconds=self._settings.scene_transition_duration,
        )
        return Storyboard(
            document_id=document.id,
            plan=plan,
            scenes=fitted_scenes,
            timeline=video_timeline,
        )

    def _fit_duration_budget(self, scenes: list[Scene], plan: VideoPlan) -> list[Scene]:
        fitted = fit_scene_durations(
            scenes,
            max_video_duration_seconds=plan.target_video_duration_seconds,
            transition_duration_seconds=self._settings.scene_transition_duration,
            min_scene_duration_seconds=plan.min_scene_duration_seconds,
            update_duration=lambda scene, duration: scene.model_copy(
                update={"duration_seconds": round(duration, 3)},
            ),
        )
        return [self._rebalance_scene_shots(scene) for scene in fitted]

    def _rebalance_scene_shots(self, scene: Scene) -> Scene:
        return self._timeline_builder.finalize_scene(scene)

    def _with_title_page_scene(
        self,
        document: Document,
        content_plan: ContentPlan,
        scenes: list[Scene],
        plan: VideoPlan,
    ) -> list[Scene]:
        """Prepend a full first-page scene so the video opens on the paper cover."""
        if not document.pages or not content_plan.selected_sections:
            return scenes

        section = content_plan.selected_sections[0]
        first_page_number = document.pages[0].page_number
        intro_shot = self._camera_planner.shot_for_page(
            document=document,
            page_number=first_page_number,
            paragraph=1,
            goal="Show the paper title page",
            duration_seconds=plan.title_page_duration_seconds,
            framing="wide",
        )
        intro = Scene(
            id=f"{document.id}-scene-intro",
            section_id=section.id,
            order=0,
            goal="Show the paper title page",
            duration_seconds=plan.title_page_duration_seconds,
            source=SceneSource(
                section=section.title,
                page=first_page_number,
                paragraph=1,
            ),
            shots=[intro_shot],
            visual=SceneVisual(page=intro_shot.page, crop=intro_shot.crop),
        )
        shifted = [
            scene.model_copy(update={"order": index}) for index, scene in enumerate(scenes, start=1)
        ]
        return [intro, *shifted]


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
