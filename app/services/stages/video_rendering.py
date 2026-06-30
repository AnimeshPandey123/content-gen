"""Video rendering stage."""

from app.config import Settings, get_settings
from app.models.pipeline import RenderResult, ScriptPlan
from app.models.video_project import VideoProject
from app.render.pipeline import RenderPipeline
from app.workflows.stage import Stage


class VideoRenderingStage(Stage[ScriptPlan, RenderResult]):
    """Generate screenshots, narration, subtitles, and the final MP4."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        render_pipeline: RenderPipeline | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._render_pipeline = render_pipeline or RenderPipeline(settings=self._settings)

    @property
    def name(self) -> str:
        return "video_rendering"

    def run(self, input_model: ScriptPlan) -> RenderResult:
        storyboard_result = input_model.storyboard_result
        document = storyboard_result.content_plan.document

        artifacts = self._render_pipeline.run(input_model)
        project = VideoProject(
            document=document,
            storyboard=storyboard_result.storyboard,
            script=input_model.script,
            artifacts=artifacts,
            output_path=artifacts.video_path,
        )

        return RenderResult(
            project=project,
            video_path=artifacts.video_path,
            artifacts=artifacts,
            success=True,
        )
