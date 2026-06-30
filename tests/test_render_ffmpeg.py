"""Unit tests for FFmpeg rendering helpers."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from app.config import Settings
from app.render.ffmpeg import FFmpegError, FFmpegRenderer


def test_render_scene_invokes_ffmpeg(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def _fake_run(command, **kwargs):
        calls.append(command)
        return MagicMock(returncode=0, stderr="")

    monkeypatch.setattr("app.render.ffmpeg.subprocess.run", _fake_run)
    renderer = FFmpegRenderer(settings=Settings(camera_motion="zoom"))
    output_path = tmp_path / "scene.mp4"

    renderer.render_scene(
        image_path=str(tmp_path / "scene.png"),
        audio_path=str(tmp_path / "scene.wav"),
        subtitle_path=str(tmp_path / "scene.ass"),
        output_path=output_path,
        duration_seconds=5.0,
    )

    assert calls
    vf_args = calls[0]
    vf_index = vf_args.index("-vf")
    assert "zoompan" in vf_args[vf_index + 1]


def test_concat_clips_writes_concat_file(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def _fake_run(command, **kwargs):
        calls.append(command)
        return MagicMock(returncode=0, stderr="")

    monkeypatch.setattr("app.render.ffmpeg.subprocess.run", _fake_run)
    clip_paths = [tmp_path / "scene_01.mp4", tmp_path / "scene_02.mp4"]
    for clip in clip_paths:
        clip.write_text("clip", encoding="utf-8")

    renderer = FFmpegRenderer(settings=Settings())
    output_path = tmp_path / "final.mp4"
    renderer.concat_clips(clip_paths, output_path)

    concat_file = tmp_path / "concat_list.txt"
    assert concat_file.exists()
    assert calls


def test_run_raises_on_ffmpeg_failure(monkeypatch) -> None:
    def _fake_run(command, **kwargs):
        return MagicMock(returncode=1, stderr="codec failed")

    monkeypatch.setattr("app.render.ffmpeg.subprocess.run", _fake_run)
    renderer = FFmpegRenderer(settings=Settings())

    with pytest.raises(FFmpegError, match="codec failed"):
        renderer._run(["-version"])


def test_run_raises_when_ffmpeg_missing(monkeypatch) -> None:
    def _fake_run(command, **kwargs):
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr("app.render.ffmpeg.subprocess.run", _fake_run)
    renderer = FFmpegRenderer(settings=Settings(ffmpeg_path="missing-ffmpeg"))

    with pytest.raises(FFmpegError, match="FFmpeg not found"):
        renderer._run(["-version"])
