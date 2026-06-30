"""Generate narration audio assets for script scenes."""

import struct
import wave
from pathlib import Path

from app.config import Settings, get_settings
from app.models.render import RenderProject, SceneAudio
from app.models.script import ScriptScene
from app.render.audio import fit_audio_to_duration, probe_wav_duration
from app.render.project import audio_path


class VoiceGeneratorError(Exception):
    """Raised when narration audio cannot be generated."""


NARRATION_STYLE_PROMPT = (
    "Read the following narration in a clear, energetic documentary voice. "
    "Use the same steady pace and tone as a short-form science explainer:\n\n"
)


def format_narration_text(text: str) -> str:
    """Wrap script text so TTS keeps a consistent delivery across scenes."""
    cleaned = text.strip()
    if not cleaned:
        return cleaned
    return f"{NARRATION_STYLE_PROMPT}{cleaned}"


class VoiceSynthesizer:
    """Protocol-compatible synthesizer that writes narration WAV files."""

    def synthesize(self, text: str, output_path: Path, *, duration_seconds: float) -> float:
        """Write audio to output_path and return the actual duration in seconds."""
        raise NotImplementedError


class WaveVoiceSynthesizer(VoiceSynthesizer):
    """Write a silent mono WAV file with duration matched to the script scene."""

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


class GeminiVoiceSynthesizer(VoiceSynthesizer):
    """Generate narration audio with Gemini text-to-speech."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        voice_name: str,
        sample_rate: int = 24000,
        settings: Settings | None = None,
    ) -> None:
        if not api_key:
            raise VoiceGeneratorError("GEMINI_API_KEY is required for Gemini TTS")

        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._voice_name = voice_name
        self._sample_rate = sample_rate
        self._settings = settings

    def synthesize(self, text: str, output_path: Path, *, duration_seconds: float) -> float:
        from google.genai import types

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=format_narration_text(text),
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=self._voice_name,
                            ),
                        ),
                    ),
                ),
            )
        except Exception as exc:
            raise VoiceGeneratorError(f"Gemini TTS request failed: {exc}") from exc

        pcm = self._extract_pcm(response)
        actual_duration = self._write_pcm_wav(output_path, pcm)
        return self._fit_to_scene_duration(output_path, duration_seconds, actual_duration)

    def _fit_to_scene_duration(
        self,
        output_path: Path,
        target_seconds: float,
        actual_duration: float,
    ) -> float:
        settings = getattr(self, "_settings", None)
        if settings is None:
            return actual_duration

        if not settings.tts_fit_scene_duration:
            return actual_duration

        return fit_audio_to_duration(
            input_path=output_path,
            target_seconds=target_seconds,
            ffmpeg_path=settings.ffmpeg_path,
            max_tempo=settings.tts_max_tempo,
        )

    def _extract_pcm(self, response: object) -> bytes:
        candidates = getattr(response, "candidates", None)
        if not candidates:
            raise VoiceGeneratorError("Gemini TTS returned no audio candidates")

        content = candidates[0].content
        parts = getattr(content, "parts", None) if content else None
        if not parts:
            raise VoiceGeneratorError("Gemini TTS returned no audio parts")

        inline_data = parts[0].inline_data
        pcm = getattr(inline_data, "data", None) if inline_data else None
        if not pcm:
            raise VoiceGeneratorError("Gemini TTS returned empty audio data")

        return pcm

    def _write_pcm_wav(self, output_path: Path, pcm: bytes) -> float:
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self._sample_rate)
            wav_file.writeframes(pcm)

        frame_count = len(pcm) // 2
        return frame_count / self._sample_rate


def build_voice_synthesizer(settings: Settings | None = None) -> VoiceSynthesizer:
    """Return the configured voice synthesizer."""
    settings = settings or get_settings()

    if settings.voice_synthesizer == "silent":
        return WaveVoiceSynthesizer()

    if not settings.gemini_api_key:
        raise VoiceGeneratorError(
            "GEMINI_API_KEY is required for Gemini TTS (set VOICE_SYNTHESIZER=silent to disable)",
        )

    return GeminiVoiceSynthesizer(
        api_key=settings.gemini_api_key,
        model=settings.tts_model,
        voice_name=settings.tts_voice,
        sample_rate=settings.tts_sample_rate,
        settings=settings,
    )


class VoiceGenerator:
    """Feature 11: generate one narration WAV asset per scene."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        synthesizer: VoiceSynthesizer | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._synthesizer = synthesizer or build_voice_synthesizer(self._settings)

    def produce(self, project: RenderProject) -> list[SceneAudio]:
        project_dir = Path(project.project_dir)
        audio_dir = project_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        audio_files: list[SceneAudio] = []
        for script_scene in project.script_plan.script.scenes:
            output_path = audio_path(project_dir, script_scene.scene)
            actual_duration = self._synthesizer.synthesize(
                script_scene.voice,
                output_path,
                duration_seconds=self._scene_duration(script_scene),
            )
            actual_duration = probe_wav_duration(output_path)
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
        return script_scene.duration
