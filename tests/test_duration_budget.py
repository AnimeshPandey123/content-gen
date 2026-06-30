"""Unit tests for video duration budgeting."""

import pytest
from app.services.duration_budget import (
    fit_scene_durations,
    playback_duration,
    recommended_content_scene_count,
)


def test_playback_duration_subtracts_crossfade_overlap() -> None:
    duration = playback_duration([5.0, 5.0, 5.0], transition_duration_seconds=0.5)
    assert duration == pytest.approx(14.0)


def test_playback_duration_returns_zero_for_empty_list() -> None:
    assert playback_duration([], transition_duration_seconds=0.5) == 0.0


def test_recommended_content_scene_count_respects_video_budget() -> None:
    count = recommended_content_scene_count(
        max_video_duration_seconds=30.0,
        title_page_duration_seconds=4.0,
        transition_duration_seconds=0.5,
        min_scene_duration_seconds=3.0,
        configured_max=4,
    )
    assert count == 4


def test_recommended_content_scene_count_returns_one_when_title_exceeds_budget() -> None:
    count = recommended_content_scene_count(
        max_video_duration_seconds=4.0,
        title_page_duration_seconds=5.0,
        transition_duration_seconds=0.5,
        min_scene_duration_seconds=3.0,
        configured_max=8,
    )
    assert count == 1


def test_fit_scene_durations_returns_empty_list_unchanged() -> None:
    assert (
        fit_scene_durations(
            [],
            max_video_duration_seconds=30.0,
            transition_duration_seconds=0.5,
            min_scene_duration_seconds=3.0,
            update_duration=lambda scene, duration: scene,
        )
        == []
    )


def test_fit_scene_durations_stops_trimming_when_scenes_hit_minimum() -> None:
    class _Scene:
        def __init__(self, duration_seconds: float) -> None:
            self.duration_seconds = duration_seconds

    scenes = [_Scene(10.0), _Scene(10.0), _Scene(10.0), _Scene(10.0)]
    fitted = fit_scene_durations(
        scenes,
        max_video_duration_seconds=10.0,
        transition_duration_seconds=0.5,
        min_scene_duration_seconds=3.0,
        update_duration=lambda scene, duration: _Scene(duration),
    )

    assert all(scene.duration_seconds == 3.0 for scene in fitted)


def test_fit_scene_durations_scales_down_long_storyboards() -> None:
    class _Scene:
        def __init__(self, duration_seconds: float) -> None:
            self.duration_seconds = duration_seconds

    scenes = [_Scene(10.0), _Scene(10.0), _Scene(10.0), _Scene(10.0)]
    fitted = fit_scene_durations(
        scenes,
        max_video_duration_seconds=30.0,
        transition_duration_seconds=0.5,
        min_scene_duration_seconds=3.0,
        update_duration=lambda scene, duration: _Scene(duration),
    )

    result = playback_duration(
        [scene.duration_seconds for scene in fitted],
        transition_duration_seconds=0.5,
    )
    assert result <= 30.0


def test_fit_scene_durations_leaves_short_storyboards_unchanged() -> None:
    class _Scene:
        def __init__(self, duration_seconds: float) -> None:
            self.duration_seconds = duration_seconds

    scenes = [_Scene(4.0), _Scene(5.0)]
    fitted = fit_scene_durations(
        scenes,
        max_video_duration_seconds=30.0,
        transition_duration_seconds=0.5,
        min_scene_duration_seconds=3.0,
        update_duration=lambda scene, duration: _Scene(duration),
    )

    assert [scene.duration_seconds for scene in fitted] == [4.0, 5.0]
