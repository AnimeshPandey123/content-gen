"""Unit tests for camera motion filters."""

from app.render.camera import build_video_filter


def test_build_video_filter_static_motion() -> None:
    result = build_video_filter(
        motion="static",
        width=1080,
        height=1920,
        fps=30,
        duration_seconds=5.0,
    )
    assert "fps=30" in result
    assert "ass=" not in result


def test_build_video_filter_zoom_motion() -> None:
    result = build_video_filter(
        motion="zoom",
        width=1080,
        height=1920,
        fps=30,
        duration_seconds=5.0,
    )
    assert "zoompan" in result


def test_build_video_filter_pan_motion() -> None:
    result = build_video_filter(
        motion="pan",
        width=1080,
        height=1920,
        fps=30,
        duration_seconds=5.0,
    )
    assert "x+2" in result


def test_build_video_filter_highlight_motion() -> None:
    result = build_video_filter(
        motion="highlight",
        width=1080,
        height=1920,
        fps=30,
        duration_seconds=5.0,
    )
    assert "drawbox" in result


def test_build_video_filter_ken_burns_default() -> None:
    result = build_video_filter(
        motion="ken_burns",
        width=1080,
        height=1920,
        fps=30,
        duration_seconds=5.0,
        ass_path="/tmp/scene.ass",
    )
    assert "zoompan" in result
    assert "ass=" in result
