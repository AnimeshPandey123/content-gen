"""Unit tests for Chatterbox voice synthesis."""

import io
import struct
import urllib.error
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from app.config import Settings
from app.render.voice import (
    ChatterboxVoiceSynthesizer,
    VoiceGeneratorError,
    build_voice_synthesizer,
)


def _wav_bytes(duration_seconds: float, sample_rate: int = 24000) -> bytes:
    frame_count = int(duration_seconds * sample_rate)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(struct.pack("<h", 1000) * frame_count)
    return buffer.getvalue()


def _mock_urlopen(response_bytes: bytes) -> MagicMock:
    mock_response = MagicMock()
    mock_response.read.return_value = response_bytes
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False
    return mock_response


def test_build_voice_synthesizer_returns_chatterbox_when_configured() -> None:
    synthesizer = build_voice_synthesizer(
        Settings(_env_file=None, voice_synthesizer="chatterbox"),
    )
    assert isinstance(synthesizer, ChatterboxVoiceSynthesizer)


def test_chatterbox_voice_synthesizer_writes_wav(tmp_path: Path) -> None:
    wav_bytes = _wav_bytes(1.0)
    with patch(
        "urllib.request.urlopen",
        return_value=_mock_urlopen(wav_bytes),
    ) as mock_urlopen:
        synthesizer = ChatterboxVoiceSynthesizer(api_url="http://127.0.0.1:4123")
        output_path = tmp_path / "scene01.wav"
        duration = synthesizer.synthesize("Hello world", output_path, duration_seconds=5.0)

    assert duration == pytest.approx(1.0, rel=0.01)
    assert output_path.exists()
    with wave.open(str(output_path), "rb") as wav_file:
        assert wav_file.getframerate() == 24000
        assert wav_file.getnframes() > 0

    request = mock_urlopen.call_args.args[0]
    assert request.full_url == "http://127.0.0.1:4123/v1/audio/speech"
    assert request.data is not None
    payload = request.data.decode()
    assert '"input": "Hello world"' in payload
    assert '"voice"' not in payload


def test_chatterbox_voice_synthesizer_includes_voice_name(tmp_path: Path) -> None:
    wav_bytes = _wav_bytes(1.0)
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(wav_bytes)) as mock_urlopen:
        synthesizer = ChatterboxVoiceSynthesizer(
            api_url="http://127.0.0.1:4123/",
            voice="my-custom-voice",
        )
        synthesizer.synthesize("Hello", tmp_path / "scene01.wav", duration_seconds=2.0)

    request = mock_urlopen.call_args.args[0]
    assert '"voice": "my-custom-voice"' in request.data.decode()


def test_chatterbox_voice_synthesizer_fits_long_audio_to_scene_budget(
    monkeypatch,
    tmp_path: Path,
) -> None:
    wav_bytes = _wav_bytes(8.0)
    fitted: list[float] = []

    def _fake_fit(**kwargs):
        fitted.append(kwargs["target_seconds"])
        return 6.0

    monkeypatch.setattr("app.render.voice.fit_audio_to_duration", _fake_fit)

    with patch("urllib.request.urlopen", return_value=_mock_urlopen(wav_bytes)):
        synthesizer = ChatterboxVoiceSynthesizer(
            api_url="http://127.0.0.1:4123",
            settings=Settings(_env_file=None, tts_fit_scene_duration=True),
        )
        duration = synthesizer.synthesize(
            "Hello world",
            tmp_path / "scene01.wav",
            duration_seconds=6.0,
        )

    assert fitted == [6.0]
    assert duration == 6.0


def test_chatterbox_voice_synthesizer_skips_fit_when_disabled(tmp_path: Path) -> None:
    wav_bytes = _wav_bytes(8.0)
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(wav_bytes)):
        synthesizer = ChatterboxVoiceSynthesizer(
            api_url="http://127.0.0.1:4123",
            settings=Settings(_env_file=None, tts_fit_scene_duration=False),
        )
        duration = synthesizer.synthesize(
            "Hello world",
            tmp_path / "scene01.wav",
            duration_seconds=6.0,
        )

    assert duration == pytest.approx(8.0, rel=0.01)


def test_chatterbox_voice_synthesizer_raises_on_blank_text(tmp_path: Path) -> None:
    synthesizer = ChatterboxVoiceSynthesizer(api_url="http://127.0.0.1:4123")
    with pytest.raises(VoiceGeneratorError, match="non-empty narration text"):
        synthesizer.synthesize("   ", tmp_path / "scene01.wav", duration_seconds=1.0)


def test_chatterbox_voice_synthesizer_raises_when_api_fails(tmp_path: Path) -> None:
    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        synthesizer = ChatterboxVoiceSynthesizer(api_url="http://127.0.0.1:4123")
        with pytest.raises(VoiceGeneratorError, match="Chatterbox TTS request failed"):
            synthesizer.synthesize("Hello", tmp_path / "scene01.wav", duration_seconds=1.0)


def test_chatterbox_voice_synthesizer_raises_on_http_error(tmp_path: Path) -> None:
    error = urllib.error.HTTPError(
        url="http://127.0.0.1:4123/v1/audio/speech",
        code=500,
        msg="Internal Server Error",
        hdrs=None,
        fp=io.BytesIO(b"server exploded"),
    )
    with patch("urllib.request.urlopen", side_effect=error):
        synthesizer = ChatterboxVoiceSynthesizer(api_url="http://127.0.0.1:4123")
        with pytest.raises(VoiceGeneratorError, match="500"):
            synthesizer.synthesize("Hello", tmp_path / "scene01.wav", duration_seconds=1.0)


def test_chatterbox_voice_synthesizer_raises_on_empty_response(tmp_path: Path) -> None:
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(b"")):
        synthesizer = ChatterboxVoiceSynthesizer(api_url="http://127.0.0.1:4123")
        with pytest.raises(VoiceGeneratorError, match="empty audio data"):
            synthesizer.synthesize("Hello", tmp_path / "scene01.wav", duration_seconds=1.0)
