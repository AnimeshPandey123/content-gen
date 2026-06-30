"""Feature 10: subtitle asset generation stage."""

from app.config import Settings, get_settings
from app.models.render import RenderProject, SceneAudio
from app.render.subtitles import SubtitleGenerator
from app.workflows.stage import Stage


class SubtitleGenerationStage(Stage[RenderProject, RenderProject]):
    """Produce ASS subtitle assets aligned to narration audio."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        generator: SubtitleGenerator | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._generator = generator or SubtitleGenerator(settings=self._settings)

    @property
    def name(self) -> str:
        return "subtitle_generation"

    def run(self, input_model: RenderProject) -> RenderProject:
        audio_models = [
            SceneAudio(
                scene_id=scene.scene_id,
                audio_path=scene.audio_path,
                duration_seconds=scene.audio_duration_seconds,
            )
            for scene in input_model.scenes
            if scene.audio_path and scene.audio_duration_seconds
        ]
        subtitles = self._generator.produce(input_model, audio_models)
        return input_model.with_subtitles(subtitles)
