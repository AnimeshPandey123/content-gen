"""Generate narration audio files for script scenes."""

import struct
import wave
from pathlib import Path

from app.config import Settings, get_settings
from app.models.pipeline import ScriptPlan
from app.models.render import SceneAudio
from app.models.script import ScriptScene


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
    """Generate one narration WAV file per script scene."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        synthesizer: VoiceSynthesizer | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._synthesizer = synthesizer or WaveVoiceSynthesizer()

    def generate(self, script_plan: ScriptPlan) -> list[SceneAudio]:
        output_dir = self._audio_dir(script_plan)
        output_dir.mkdir(parents=True, exist_ok=True)

        audio_files: list[SceneAudio] = []
        for script_scene in script_plan.script.scenes:
            duration = self._scene_duration(script_scene)
            filename = f"scene_{script_scene.scene:02d}.wav"
            audio_path = output_dir / filename
            actual_duration = self._synthesizer.synthesize(
                script_scene.voice,
                audio_path,
                duration_seconds=duration,
            )
            audio_files.append(
                SceneAudio(
                    scene_id=script_scene.scene_id,
                    audio_path=str(audio_path.resolve()),
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

    def _audio_dir(self, script_plan: ScriptPlan) -> Path:
        document_id = script_plan.storyboard_result.content_plan.document.id
        return self._settings.output_dir / document_id / "audio"
