"""Unit tests for camera motion filters."""

import pytest
from app.render.camera import build_clip_transition_filter, build_video_filter


def test_build_video_filter_static_motion() -> None:
    result = build_video_filter(
        motion="static",
        width=1080,
        height=1920,
        fps=30,
        duration_seconds=5.0,
    )
    assert "fps=30" in result
    assert "crop=1080:1920" in result
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


def test_build_video_filter_ken_burns_is_static_for_now() -> None:
    result = build_video_filter(
        motion="ken_burns",
        width=1080,
        height=1920,
        fps=30,
        duration_seconds=5.0,
        ass_path="/tmp/scene.ass",
    )
    assert "zoompan" not in result
    assert "fps=30" in result
    assert "ass=" in result


def test_build_video_filter_unknown_motion_falls_back_to_static() -> None:
    result = build_video_filter(
        motion="unknown",
        width=1080,
        height=1920,
        fps=30,
        duration_seconds=5.0,
    )
    assert "zoompan" not in result
    assert "fps=30" in result


def test_build_clip_transition_filter_requires_multiple_clips() -> None:
    with pytest.raises(ValueError, match="At least two clips"):
        build_clip_transition_filter(clip_count=1, durations=[5.0], transition_duration=0.5)


def test_build_clip_transition_filter_chains_crossfades() -> None:
    result = build_clip_transition_filter(
        clip_count=3,
        durations=[5.0, 4.0, 6.0],
        transition_duration=0.5,
    )

    assert result.count("xfade") == 2
    assert result.count("acrossfade") == 2
    assert "offset=4.500" in result
