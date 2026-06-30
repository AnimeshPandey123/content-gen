"""Feature 11: voice asset generation stage."""

from app.config import Settings, get_settings
from app.models.render import RenderProject
from app.render.voice import VoiceGenerator
from app.workflows.stage import Stage


class VoiceGenerationStage(Stage[RenderProject, RenderProject]):
    """Produce narration WAV assets from script voice text."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        generator: VoiceGenerator | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._generator = generator or VoiceGenerator(settings=self._settings)

    @property
    def name(self) -> str:
        return "voice_generation"

    def run(self, input_model: RenderProject) -> RenderProject:
        audio_files = self._generator.produce(input_model)
        return input_model.with_audio(audio_files)
