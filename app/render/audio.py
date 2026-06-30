"""Audio helpers for narration timing and FFmpeg adjustments."""

import shutil
import subprocess
import textwrap
import wave
from pathlib import Path


class AudioProcessingError(Exception):
    """Raised when narration audio cannot be processed."""


def probe_wav_duration(path: Path) -> float:
    """Return the duration of a mono/stereo WAV file in seconds."""
    with wave.open(str(path), "rb") as wav_file:
        frame_rate = wav_file.getframerate()
        if frame_rate <= 0:
            raise AudioProcessingError(f"Invalid sample rate in {path}")
        return wav_file.getnframes() / frame_rate


def fit_audio_to_duration(
    *,
    input_path: Path,
    target_seconds: float,
    ffmpeg_path: str = "ffmpeg",
    max_tempo: float = 1.35,
    tolerance: float = 0.05,
) -> float:
    """Speed up narration slightly when TTS runs longer than the scene budget."""
    actual = probe_wav_duration(input_path)
    if actual <= target_seconds * (1 + tolerance):
        return actual

    tempo = min(actual / target_seconds, max_tempo)
    temp_path = input_path.with_suffix(".fitted.wav")
    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(input_path),
        "-filter:a",
        f"atempo={tempo:.3f}",
        str(temp_path),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise AudioProcessingError(f"FFmpeg not found: {ffmpeg_path}") from exc

    if result.returncode != 0:
        stderr = textwrap.shorten(result.stderr or "ffmpeg failed", width=300)
        raise AudioProcessingError(stderr)

    shutil.move(temp_path, input_path)
    return probe_wav_duration(input_path)
