"""Generate narration audio assets for script scenes."""

import struct
import wave
from pathlib import Path

from app.config import Settings, get_settings
from app.models.render import RenderProject, SceneAudio
from app.models.script import ScriptScene
from app.render.project import audio_path


class VoiceGeneratorError(Exception):
    """Raised when narration audio cannot be generated."""


class VoiceSynthesizer:
    """Protocol-compatible synthesizer that writes narration WAV files."""

    def synthesize(self, text: str, output_path: Path, *, duration_seconds: float) -> float:
        """Write audio to output_path and return the actual duration in seconds."""
        raise NotImplementedError


class WaveVoiceSynthesizer(VoiceSynthesizer):
    """Write a mono WAV file with duration matched to the script scene."""

    def __init__(self, *, sample_rate: int = 22050) -> None:
        self._sample_rate = sample_rate

    def synthesize(self, text: str, output_path: Path, *, duration_seconds: float) -> float:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        frame_count = max(int(duration_seconds * self._sample_rate), 1)
        with wave.open(str(output_path), "w") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self._sample_rate)
            wav_file.writeframes(struct.pack("<h", 0) * frame_count)
        return frame_count / self._sample_rate


class VoiceGenerator:
    """Feature 11: generate one narration WAV asset per scene."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        synthesizer: VoiceSynthesizer | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._synthesizer = synthesizer or WaveVoiceSynthesizer()

    def produce(self, project: RenderProject) -> list[SceneAudio]:
        project_dir = Path(project.project_dir)
        audio_dir = project_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        audio_files: list[SceneAudio] = []
        for script_scene in project.script_plan.script.scenes:
            duration = self._scene_duration(script_scene)
            output_path = audio_path(project_dir, script_scene.scene)
            actual_duration = self._synthesizer.synthesize(
                script_scene.voice,
                output_path,
                duration_seconds=duration,
            )
            audio_files.append(
                SceneAudio(
                    scene_id=script_scene.scene_id,
                    audio_path=str(output_path.resolve()),
                    duration_seconds=actual_duration,
                ),
            )

        return audio_files

    def estimate_duration(self, text: str) -> float:
        """Estimate narration duration from word count and configured speaking rate."""
        words = max(len(text.split()), 1)
        minutes = words / self._settings.words_per_minute
        return max(minutes * 60.0 / self._settings.narration_speed, 1.0)

    def _scene_duration(self, script_scene: ScriptScene) -> float:
        estimated = self.estimate_duration(script_scene.voice)
        return max(script_scene.duration, estimated)
