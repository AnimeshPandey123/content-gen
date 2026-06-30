"""Unit tests for Gemini and placeholder voice synthesis."""

import struct
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from app.config import Settings
from app.render.voice import (
    GeminiVoiceSynthesizer,
    VoiceGeneratorError,
    WaveVoiceSynthesizer,
    build_voice_synthesizer,
)


def _pcm_bytes(duration_seconds: float, sample_rate: int = 24000) -> bytes:
    frame_count = int(duration_seconds * sample_rate)
    return struct.pack("<h", 1000) * frame_count


def test_build_voice_synthesizer_returns_gemini_when_configured() -> None:
    synthesizer = build_voice_synthesizer(
        Settings(_env_file=None, gemini_api_key="test-key", voice_synthesizer="gemini"),
    )
    assert isinstance(synthesizer, GeminiVoiceSynthesizer)


def test_build_voice_synthesizer_returns_silent_backend() -> None:
    synthesizer = build_voice_synthesizer(
        Settings(_env_file=None, voice_synthesizer="silent"),
    )
    assert isinstance(synthesizer, WaveVoiceSynthesizer)


def test_build_voice_synthesizer_requires_api_key_for_gemini() -> None:
    with pytest.raises(VoiceGeneratorError, match="GEMINI_API_KEY"):
        build_voice_synthesizer(
            Settings(_env_file=None, voice_synthesizer="gemini", gemini_api_key=None),
        )


def test_gemini_voice_synthesizer_requires_api_key() -> None:
    with pytest.raises(VoiceGeneratorError, match="GEMINI_API_KEY"):
        GeminiVoiceSynthesizer(api_key="", model="gemini-2.5-flash-preview-tts", voice_name="Kore")


def test_gemini_voice_synthesizer_writes_wav(tmp_path: Path) -> None:
    pcm = _pcm_bytes(1.0)
    mock_response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[SimpleNamespace(inline_data=SimpleNamespace(data=pcm))],
                ),
            ),
        ],
    )
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch("google.genai.Client", return_value=mock_client):
        synthesizer = GeminiVoiceSynthesizer(
            api_key="test-key",
            model="gemini-2.5-flash-preview-tts",
            voice_name="Kore",
            sample_rate=24000,
        )
        output_path = tmp_path / "scene01.wav"
        duration = synthesizer.synthesize("Hello world", output_path, duration_seconds=5.0)

    assert duration == pytest.approx(1.0, rel=0.01)
    assert output_path.exists()
    with wave.open(str(output_path), "rb") as wav_file:
        assert wav_file.getframerate() == 24000
        assert wav_file.getnframes() > 0


def test_gemini_voice_synthesizer_fits_long_audio_to_scene_budget(
    monkeypatch,
    tmp_path: Path,
) -> None:
    pcm = _pcm_bytes(8.0)
    mock_response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[SimpleNamespace(inline_data=SimpleNamespace(data=pcm))],
                ),
            ),
        ],
    )
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    fitted: list[float] = []

    def _fake_fit(**kwargs):
        fitted.append(kwargs["target_seconds"])
        return 6.0

    monkeypatch.setattr("app.render.voice.fit_audio_to_duration", _fake_fit)

    with patch("google.genai.Client", return_value=mock_client):
        synthesizer = GeminiVoiceSynthesizer(
            api_key="test-key",
            model="gemini-2.5-flash-preview-tts",
            voice_name="Kore",
            settings=Settings(_env_file=None, tts_fit_scene_duration=True),
        )
        duration = synthesizer.synthesize(
            "Hello world",
            tmp_path / "scene01.wav",
            duration_seconds=6.0,
        )

    assert fitted == [6.0]
    assert duration == 6.0


def test_gemini_voice_synthesizer_skips_fit_when_disabled(tmp_path: Path) -> None:
    pcm = _pcm_bytes(8.0)
    mock_response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[SimpleNamespace(inline_data=SimpleNamespace(data=pcm))],
                ),
            ),
        ],
    )
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch("google.genai.Client", return_value=mock_client):
        synthesizer = GeminiVoiceSynthesizer(
            api_key="test-key",
            model="gemini-2.5-flash-preview-tts",
            voice_name="Kore",
            settings=Settings(_env_file=None, tts_fit_scene_duration=False),
        )
        duration = synthesizer.synthesize(
            "Hello world",
            tmp_path / "scene01.wav",
            duration_seconds=6.0,
        )

    assert duration == pytest.approx(8.0, rel=0.01)


def test_gemini_voice_synthesizer_skips_fit_without_settings(tmp_path: Path) -> None:
    pcm = _pcm_bytes(2.0)
    mock_response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[SimpleNamespace(inline_data=SimpleNamespace(data=pcm))],
                ),
            ),
        ],
    )
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch("google.genai.Client", return_value=mock_client):
        synthesizer = GeminiVoiceSynthesizer(
            api_key="test-key",
            model="gemini-2.5-flash-preview-tts",
            voice_name="Kore",
        )
        duration = synthesizer.synthesize(
            "Hello world",
            tmp_path / "scene01.wav",
            duration_seconds=1.0,
        )

    assert duration == pytest.approx(2.0, rel=0.01)


def test_gemini_voice_synthesizer_raises_when_api_fails(tmp_path: Path) -> None:
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("network error")

    with patch("google.genai.Client", return_value=mock_client):
        synthesizer = GeminiVoiceSynthesizer(
            api_key="test-key",
            model="gemini-2.5-flash-preview-tts",
            voice_name="Kore",
        )
        with pytest.raises(VoiceGeneratorError, match="Gemini TTS request failed"):
            synthesizer.synthesize("Hello", tmp_path / "scene01.wav", duration_seconds=1.0)


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (SimpleNamespace(candidates=[]), "no audio candidates"),
        (
            SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[]))]),
            "no audio parts",
        ),
        (
            SimpleNamespace(
                candidates=[
                    SimpleNamespace(
                        content=SimpleNamespace(parts=[SimpleNamespace(inline_data=None)]),
                    ),
                ],
            ),
            "empty audio data",
        ),
    ],
)
def test_gemini_voice_synthesizer_raises_on_invalid_response(
    tmp_path: Path,
    response: object,
    message: str,
) -> None:
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = response

    with patch("google.genai.Client", return_value=mock_client):
        synthesizer = GeminiVoiceSynthesizer(
            api_key="test-key",
            model="gemini-2.5-flash-preview-tts",
            voice_name="Kore",
        )
        with pytest.raises(VoiceGeneratorError, match=message):
            synthesizer.synthesize("Hello", tmp_path / "scene01.wav", duration_seconds=1.0)
