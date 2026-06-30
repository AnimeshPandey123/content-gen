"""Feature 8: screenshot asset generation stage."""

from app.config import Settings, get_settings
from app.models.pipeline import ScriptPlan
from app.models.render import RenderProject
from app.render.project import bootstrap_render_project
from app.render.screenshot import ScreenshotGenerator
from app.workflows.stage import Stage


class ScreenshotGenerationStage(Stage[ScriptPlan, RenderProject]):
    """Produce cropped PNG screenshots from storyboard visual instructions."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        generator: ScreenshotGenerator | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._generator = generator or ScreenshotGenerator(settings=self._settings)

    @property
    def name(self) -> str:
        return "screenshot_generation"

    def run(self, input_model: ScriptPlan) -> RenderProject:
        project = bootstrap_render_project(input_model, settings=self._settings)
        screenshots = self._generator.produce(project)
        return project.with_screenshots(screenshots)
