"""Feature 12: final video assembly stage."""

from app.config import Settings, get_settings
from app.models.pipeline import RenderResult
from app.models.render import RenderProject
from app.models.video_project import VideoProject
from app.render.assembler import VideoAssembler
from app.workflows.stage import Stage


class VideoRenderingStage(Stage[RenderProject, RenderResult]):
    """Assemble screenshot, audio, and subtitle assets into the final MP4."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        assembler: VideoAssembler | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._assembler = assembler or VideoAssembler(settings=self._settings)

    @property
    def name(self) -> str:
        return "video_rendering"

    def run(self, input_model: RenderProject) -> RenderResult:
        project = self._assembler.render(input_model)
        script_plan = project.script_plan
        document = script_plan.storyboard_result.content_plan.document

        video_project = VideoProject(
            document=document,
            storyboard=script_plan.storyboard_result.storyboard,
            script=script_plan.script,
            render_project=project,
            output_path=project.video_path,
        )

        return RenderResult(
            project=video_project,
            video_path=project.video_path or "",
            render_project=project,
            success=True,
        )
