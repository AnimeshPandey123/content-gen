"""Helpers for fitting scene durations into a target video length."""

from typing import Protocol, TypeVar

T = TypeVar("T", bound="_DurationScene")


class _DurationScene(Protocol):
    duration_seconds: float


def playback_duration(
    durations: list[float],
    *,
    transition_duration_seconds: float,
) -> float:
    """Return final video length after crossfade overlaps."""
    if not durations:
        return 0.0
    overlap = max(len(durations) - 1, 0) * transition_duration_seconds
    return sum(durations) - overlap


def recommended_content_scene_count(
    *,
    max_video_duration_seconds: float,
    title_page_duration_seconds: float,
    transition_duration_seconds: float,
    min_scene_duration_seconds: float,
    configured_max: int,
) -> int:
    """Estimate how many LLM-planned scenes fit before the title page is prepended."""
    content_budget = max_video_duration_seconds - title_page_duration_seconds
    if content_budget <= 0:
        return 1

    per_scene_cost = min_scene_duration_seconds + transition_duration_seconds
    estimated = int(content_budget // per_scene_cost)
    return max(1, min(configured_max, estimated))


def fit_scene_durations(
    scenes: list[T],
    *,
    max_video_duration_seconds: float,
    transition_duration_seconds: float,
    min_scene_duration_seconds: float,
    update_duration,
) -> list[T]:
    """Scale and trim scene durations so playback fits the target video length."""
    if not scenes:
        return scenes

    durations = [scene.duration_seconds for scene in scenes]
    durations = _scale_durations(
        durations,
        max_video_duration_seconds=max_video_duration_seconds,
        transition_duration_seconds=transition_duration_seconds,
        min_scene_duration_seconds=min_scene_duration_seconds,
    )
    return [
        update_duration(scene, duration) for scene, duration in zip(scenes, durations, strict=True)
    ]


def _scale_durations(
    durations: list[float],
    *,
    max_video_duration_seconds: float,
    transition_duration_seconds: float,
    min_scene_duration_seconds: float,
) -> list[float]:
    overlap = max(len(durations) - 1, 0) * transition_duration_seconds
    max_sum = max_video_duration_seconds + overlap
    current_sum = sum(durations)

    if current_sum <= max_sum:
        return durations

    scaled = [
        max(duration * max_sum / current_sum, min_scene_duration_seconds) for duration in durations
    ]
    return _trim_to_budget(
        scaled,
        max_video_duration_seconds=max_video_duration_seconds,
        transition_duration_seconds=transition_duration_seconds,
        min_scene_duration_seconds=min_scene_duration_seconds,
    )


def _trim_to_budget(
    durations: list[float],
    *,
    max_video_duration_seconds: float,
    transition_duration_seconds: float,
    min_scene_duration_seconds: float,
) -> list[float]:
    trimmed = list(durations)
    guard = 0
    while (
        playback_duration(trimmed, transition_duration_seconds=transition_duration_seconds)
        > max_video_duration_seconds
        and guard < 10_000
    ):
        guard += 1
        longest_index = max(
            range(len(trimmed)),
            key=lambda index: trimmed[index],
        )
        if trimmed[longest_index] <= min_scene_duration_seconds:
            break
        trimmed[longest_index] = max(
            trimmed[longest_index] - 0.1,
            min_scene_duration_seconds,
        )
    return trimmed
