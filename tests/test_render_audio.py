"""Unit tests for narration audio processing helpers."""

import struct
import wave
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from app.render.audio import AudioProcessingError, fit_audio_to_duration, probe_wav_duration


def _write_wav(path: Path, *, duration_seconds: float, sample_rate: int = 24000) -> None:
    frame_count = int(duration_seconds * sample_rate)
    with wave.open(str(path), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(struct.pack("<h", 0) * frame_count)


def test_probe_wav_duration_returns_seconds(tmp_path: Path) -> None:
    wav_path = tmp_path / "scene.wav"
    _write_wav(wav_path, duration_seconds=2.5)

    assert probe_wav_duration(wav_path) == pytest.approx(2.5)


def test_fit_audio_to_duration_returns_unchanged_when_within_tolerance(tmp_path: Path) -> None:
    wav_path = tmp_path / "scene.wav"
    _write_wav(wav_path, duration_seconds=4.0)

    duration = fit_audio_to_duration(input_path=wav_path, target_seconds=4.2)

    assert duration == pytest.approx(4.0)


def test_fit_audio_to_duration_speeds_up_long_audio(monkeypatch, tmp_path: Path) -> None:
    wav_path = tmp_path / "scene.wav"
    _write_wav(wav_path, duration_seconds=8.0)
    calls: list[list[str]] = []

    def _fake_run(command, **kwargs):
        calls.append(command)
        output_path = Path(command[-1])
        _write_wav(output_path, duration_seconds=6.0)
        return MagicMock(returncode=0, stderr="")

    monkeypatch.setattr("app.render.audio.subprocess.run", _fake_run)
    duration = fit_audio_to_duration(
        input_path=wav_path,
        target_seconds=6.0,
        max_tempo=1.35,
    )

    assert any("atempo=" in arg for arg in calls[0])
    assert duration == pytest.approx(6.0)


def test_fit_audio_to_duration_raises_when_ffmpeg_missing(monkeypatch, tmp_path: Path) -> None:
    wav_path = tmp_path / "scene.wav"
    _write_wav(wav_path, duration_seconds=8.0)

    def _fake_run(command, **kwargs):
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr("app.render.audio.subprocess.run", _fake_run)

    with pytest.raises(AudioProcessingError, match="FFmpeg not found"):
        fit_audio_to_duration(input_path=wav_path, target_seconds=5.0)


def test_fit_audio_to_duration_raises_on_ffmpeg_failure(monkeypatch, tmp_path: Path) -> None:
    wav_path = tmp_path / "scene.wav"
    _write_wav(wav_path, duration_seconds=8.0)

    def _fake_run(command, **kwargs):
        return MagicMock(returncode=1, stderr="failed")

    monkeypatch.setattr("app.render.audio.subprocess.run", _fake_run)

    with pytest.raises(AudioProcessingError, match="failed"):
        fit_audio_to_duration(input_path=wav_path, target_seconds=5.0)


def test_probe_wav_duration_raises_on_invalid_sample_rate(monkeypatch, tmp_path: Path) -> None:
    wav_path = tmp_path / "scene.wav"
    wav_path.write_bytes(b"RIFF")

    class _BadWave:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def getframerate(self):
            return 0

        def getnframes(self):
            return 100

    monkeypatch.setattr("app.render.audio.wave.open", lambda *_args, **_kwargs: _BadWave())

    with pytest.raises(AudioProcessingError, match="Invalid sample rate"):
        probe_wav_duration(wav_path)
