"""Unit tests for FFmpeg rendering helpers."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from app.config import Settings
from app.render.ffmpeg import FFmpegError, FFmpegRenderer


def test_render_scene_uses_static_motion_by_default(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def _fake_run(command, **kwargs):
        calls.append(command)
        return MagicMock(returncode=0, stderr="")

    monkeypatch.setattr("app.render.ffmpeg.subprocess.run", _fake_run)
    renderer = FFmpegRenderer(settings=Settings())
    output_path = tmp_path / "scene.mp4"

    renderer.render_scene(
        image_path=str(tmp_path / "scene.png"),
        audio_path=str(tmp_path / "scene.wav"),
        subtitle_path=str(tmp_path / "scene.ass"),
        output_path=output_path,
        duration_seconds=5.0,
    )

    vf_args = calls[0]
    vf_index = vf_args.index("-vf")
    assert "zoompan" not in vf_args[vf_index + 1]
    assert "fps=30" in vf_args[vf_index + 1]


def test_render_scene_can_still_apply_zoom_motion(monkeypatch, tmp_path: Path) -> None:
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

    vf_args = calls[0]
    vf_index = vf_args.index("-vf")
    assert "zoompan" in vf_args[vf_index + 1]


def test_concat_clips_applies_crossfade_transitions(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def _fake_run(command, **kwargs):
        calls.append(command)
        return MagicMock(returncode=0, stderr="", stdout='{"format":{"duration":"5.0"}}')

    monkeypatch.setattr("app.render.ffmpeg.subprocess.run", _fake_run)
    clip_paths = [tmp_path / "scene_01.mp4", tmp_path / "scene_02.mp4"]
    for clip in clip_paths:
        clip.write_text("clip", encoding="utf-8")

    renderer = FFmpegRenderer(settings=Settings(scene_transition="crossfade"))
    output_path = tmp_path / "final.mp4"
    renderer.concat_clips(clip_paths, output_path)

    assert calls
    command = calls[-1]
    filter_index = command.index("-filter_complex")
    assert "xfade" in command[filter_index + 1]
    assert "acrossfade" in command[filter_index + 1]


def test_concat_clips_uses_demuxer_for_cut_transitions(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def _fake_run(command, **kwargs):
        calls.append(command)
        return MagicMock(returncode=0, stderr="")

    monkeypatch.setattr("app.render.ffmpeg.subprocess.run", _fake_run)
    clip_paths = [tmp_path / "scene_01.mp4", tmp_path / "scene_02.mp4"]
    for clip in clip_paths:
        clip.write_text("clip", encoding="utf-8")

    renderer = FFmpegRenderer(settings=Settings(scene_transition="cut"))
    output_path = tmp_path / "final.mp4"
    renderer.concat_clips(clip_paths, output_path)

    concat_file = tmp_path / "concat_list.txt"
    assert concat_file.exists()
    assert "-f" in calls[-1]
    assert "concat" in calls[-1]


def test_concat_single_clip_copies_stream(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def _fake_run(command, **kwargs):
        calls.append(command)
        return MagicMock(returncode=0, stderr="")

    monkeypatch.setattr("app.render.ffmpeg.subprocess.run", _fake_run)
    clip_path = tmp_path / "scene_01.mp4"
    clip_path.write_text("clip", encoding="utf-8")

    renderer = FFmpegRenderer(settings=Settings())
    renderer.concat_clips([clip_path], tmp_path / "final.mp4")

    assert calls[-1][-3:] == ["-c", "copy", str(tmp_path / "final.mp4")]


def test_concat_clips_raises_when_clip_list_empty(tmp_path: Path) -> None:
    renderer = FFmpegRenderer(settings=Settings())

    with pytest.raises(FFmpegError, match="No scene clips"):
        renderer.concat_clips([], tmp_path / "final.mp4")


def test_ffprobe_path_falls_back_to_default_binary() -> None:
    renderer = FFmpegRenderer(settings=Settings(ffmpeg_path="avconv"))
    assert renderer._ffprobe_path() == "ffprobe"


def test_probe_duration_raises_when_ffprobe_missing(monkeypatch, tmp_path: Path) -> None:
    def _fake_run(command, **kwargs):
        raise FileNotFoundError("ffprobe")

    monkeypatch.setattr("app.render.ffmpeg.subprocess.run", _fake_run)
    renderer = FFmpegRenderer(settings=Settings())
    clip_path = tmp_path / "scene.mp4"
    clip_path.write_text("clip", encoding="utf-8")

    with pytest.raises(FFmpegError, match="ffprobe not found"):
        renderer._probe_duration(clip_path)


def test_transition_duration_clamps_for_short_clips() -> None:
    renderer = FFmpegRenderer(settings=Settings(scene_transition_duration=0.5))
    duration = renderer._transition_duration([0.5, 5.0])
    assert duration == pytest.approx(0.2, rel=0.01)


def test_probe_duration_raises_on_ffprobe_failure(monkeypatch, tmp_path: Path) -> None:
    def _fake_run(command, **kwargs):
        return MagicMock(returncode=1, stderr="probe failed", stdout="")

    monkeypatch.setattr("app.render.ffmpeg.subprocess.run", _fake_run)
    renderer = FFmpegRenderer(settings=Settings())
    clip_path = tmp_path / "scene.mp4"
    clip_path.write_text("clip", encoding="utf-8")

    with pytest.raises(FFmpegError, match="probe failed"):
        renderer._probe_duration(clip_path)


def test_ffprobe_path_derives_from_ffmpeg_binary() -> None:
    renderer = FFmpegRenderer(settings=Settings(ffmpeg_path="/usr/local/bin/ffmpeg"))
    assert renderer._ffprobe_path() == "/usr/local/bin/ffprobe"


def test_probe_duration_raises_on_invalid_payload(monkeypatch, tmp_path: Path) -> None:
    def _fake_run(command, **kwargs):
        return MagicMock(returncode=0, stderr="", stdout='{"format":{}}')

    monkeypatch.setattr("app.render.ffmpeg.subprocess.run", _fake_run)
    renderer = FFmpegRenderer(settings=Settings())
    clip_path = tmp_path / "scene.mp4"
    clip_path.write_text("clip", encoding="utf-8")

    with pytest.raises(FFmpegError, match="Could not read duration"):
        renderer._probe_duration(clip_path)


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
