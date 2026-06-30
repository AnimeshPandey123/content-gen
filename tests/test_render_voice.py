"""Unit tests for narration audio asset generation."""

from pathlib import Path

import pytest
from app.config import Settings
from app.render.project import bootstrap_render_project
from app.render.voice import VoiceGenerator, VoiceSynthesizer, WaveVoiceSynthesizer
from app.services.stages.voice_generation import VoiceGenerationStage

from tests.test_render_project import _script_plan


def test_produce_writes_scene01_wav(tmp_path: Path) -> None:
    project = bootstrap_render_project(
        _script_plan(),
        settings=Settings(output_dir=tmp_path),
    )
    generator = VoiceGenerator(settings=Settings(output_dir=tmp_path))
    audio_files = generator.produce(project)

    assert audio_files[0].audio_path.endswith("scene01.wav")
    assert Path(audio_files[0].audio_path).exists()


def test_voice_generation_stage_updates_project_assets(tmp_path: Path) -> None:
    project = bootstrap_render_project(
        _script_plan(),
        settings=Settings(output_dir=tmp_path),
    )
    result = VoiceGenerationStage(settings=Settings(output_dir=tmp_path)).run(project)

    assert result.scenes[0].audio_path is not None
    assert result.scenes[0].audio_duration_seconds is not None


def test_estimate_duration_uses_words_per_minute() -> None:
    generator = VoiceGenerator(settings=Settings(words_per_minute=150, narration_speed=1.0))
    duration = generator.estimate_duration("one two three four five six")
    assert duration >= 2.0


def test_wave_voice_synthesizer_writes_requested_duration(tmp_path: Path) -> None:
    output_path = tmp_path / "voice.wav"
    duration = WaveVoiceSynthesizer().synthesize("hello", output_path, duration_seconds=2.5)
    assert duration == pytest.approx(2.5, rel=0.01)


def test_voice_synthesizer_base_raises_not_implemented(tmp_path: Path) -> None:
    with pytest.raises(NotImplementedError):
        VoiceSynthesizer().synthesize("hello", tmp_path / "voice.wav", duration_seconds=1.0)
