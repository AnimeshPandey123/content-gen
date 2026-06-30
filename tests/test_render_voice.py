"""Unit tests for narration audio generation."""

import wave
from pathlib import Path

import pytest
from app.config import Settings
from app.models.pipeline import ContentPlan, ScriptPlan, StoryboardResult
from app.models.script import Script, ScriptScene
from app.models.section import Section
from app.models.storyboard import Storyboard
from app.render.voice import VoiceGenerator, VoiceSynthesizer, WaveVoiceSynthesizer

from tests.conftest import sample_scene
from tests.test_stages import _sample_document


def _script_plan() -> ScriptPlan:
    document = _sample_document()
    return ScriptPlan(
        storyboard_result=StoryboardResult(
            content_plan=ContentPlan(
                document=document,
                selected_sections=[
                    Section(id="sec-1", title="T", content="Sample", page_numbers=[1]),
                ],
            ),
            storyboard=Storyboard(document_id=document.id, scenes=[sample_scene(id="scene-1")]),
        ),
        script=Script(
            scenes=[
                ScriptScene(
                    scene=1,
                    scene_id="scene-1",
                    voice="This paper improves accuracy by twelve percent.",
                    overlay="12% better",
                    duration=4.0,
                ),
            ],
        ),
    )


def test_generate_writes_wav_files(tmp_path: Path) -> None:
    generator = VoiceGenerator(settings=Settings(output_dir=tmp_path))
    audio_files = generator.generate(_script_plan())

    assert len(audio_files) == 1
    audio_path = Path(audio_files[0].audio_path)
    assert audio_path.exists()
    with wave.open(str(audio_path), "r") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getframerate() == 22050


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
