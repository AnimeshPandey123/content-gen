"""Unit tests for timeline building."""

import pytest
from app.models.bounding_box import BoundingBox
from app.models.scene import Scene, SceneShot, SceneSource, SceneVisual
from app.models.timeline import SceneTimeline, TimelineSegment, VideoTimeline
from app.services.timeline_builder import TimelineBuilder


def _scene_with_shots(*, duration: float = 8.0) -> Scene:
    wide = round(duration * 0.375, 3)
    zoom = round(duration * 0.375, 3)
    highlight = round(duration - wide - zoom, 3)
    return Scene(
        id="scene-1",
        section_id="sec-1",
        order=0,
        goal="Explain the result",
        duration_seconds=duration,
        source=SceneSource(section="Results", page=1, paragraph=1),
        shots=[
            SceneShot(
                order=0,
                goal="Hook",
                duration_seconds=wide,
                page=1,
                paragraph=1,
                framing="wide",
                crop=BoundingBox(x=0, y=0, width=612, height=792),
            ),
            SceneShot(
                order=1,
                goal="Zoom",
                duration_seconds=zoom,
                page=1,
                paragraph=1,
                framing="focus",
                crop=BoundingBox(x=0, y=100, width=612, height=300),
            ),
            SceneShot(
                order=2,
                goal="Highlight",
                duration_seconds=highlight,
                page=1,
                paragraph=1,
                framing="highlight",
                crop=BoundingBox(x=72, y=200, width=400, height=120),
            ),
        ],
        visual=SceneVisual(page=1, crop=BoundingBox(x=0, y=0, width=612, height=792)),
        timeline=None,
    )


def test_build_scene_timeline_maps_shots_to_absolute_ranges() -> None:
    builder = TimelineBuilder()
    scene = _scene_with_shots(duration=8.0)
    timeline = builder.build_scene_timeline(scene)

    assert [(segment.start_seconds, segment.end_seconds, segment.goal) for segment in timeline.segments] == [
        (0.0, 3.0, "Hook"),
        (3.0, 6.0, "Zoom"),
        (6.0, 8.0, "Highlight"),
    ]


def test_finalize_scene_syncs_shot_start_and_end_times() -> None:
    builder = TimelineBuilder()
    scene = builder.finalize_scene(_scene_with_shots(duration=8.0))

    assert scene.timeline is not None
    assert scene.shots[0].start_seconds == 0.0
    assert scene.shots[0].end_seconds == 3.0
    assert scene.shots[2].end_seconds == 8.0


def test_scale_scene_timeline_resizes_segment_boundaries() -> None:
    builder = TimelineBuilder()
    timeline = builder.build_scene_timeline(_scene_with_shots(duration=8.0))
    scaled = builder.scale_scene_timeline(timeline, 6.0)

    assert scaled.duration_seconds == 6.0
    assert scaled.segments[-1].end_seconds == 6.0


def test_build_video_timeline_includes_transition_markers() -> None:
    builder = TimelineBuilder()
    scene_a = builder.finalize_scene(_scene_with_shots(duration=8.0))
    scene_b = builder.finalize_scene(
        _scene_with_shots(duration=6.0).model_copy(
            update={"id": "scene-2", "order": 1, "goal": "Takeaway"},
        ),
    )

    video_timeline = builder.build_video_timeline(
        [scene_a, scene_b],
        transition_duration_seconds=0.5,
    )

    kinds = [segment.kind for segment in video_timeline.segments]
    assert kinds.count("transition") == 1
    transition = next(segment for segment in video_timeline.segments if segment.kind == "transition")
    assert transition.start_seconds == 8.0
    assert transition.end_seconds == 8.5
    assert video_timeline.duration_seconds == pytest.approx(13.5)


def test_shot_durations_reads_from_scene_timeline() -> None:
    builder = TimelineBuilder()
    scene = builder.finalize_scene(_scene_with_shots(duration=8.0))

    assert builder.shot_durations(scene) == [3.0, 3.0, 2.0]


def test_timeline_segment_rejects_invalid_range() -> None:
    with pytest.raises(ValueError, match="end_seconds must be greater"):
        TimelineSegment(start_seconds=2.0, end_seconds=2.0, goal="Invalid")


def test_scene_timeline_requires_shot_coverage() -> None:
    with pytest.raises(ValueError, match="must end at the scene duration"):
        SceneTimeline(
            duration_seconds=8.0,
            segments=[
                TimelineSegment(start_seconds=0.0, end_seconds=3.0, goal="Hook", shot_order=0),
            ],
        )


def test_scale_scene_timeline_handles_zero_duration() -> None:
    builder = TimelineBuilder()
    timeline = SceneTimeline.model_construct(
        duration_seconds=0.0,
        segments=[
            TimelineSegment(start_seconds=0.0, end_seconds=0.001, goal="Hook", shot_order=0),
        ],
    )

    scaled = builder.scale_scene_timeline(timeline, 4.0)

    assert scaled.duration_seconds == 4.0


def test_apply_scene_timeline_skips_non_shot_segments() -> None:
    builder = TimelineBuilder()
    scene = _scene_with_shots(duration=8.0)
    timeline = SceneTimeline(
        duration_seconds=8.0,
        segments=[
            TimelineSegment(start_seconds=0.0, end_seconds=3.0, goal="Hook", shot_order=0),
            TimelineSegment(
                start_seconds=3.0,
                end_seconds=3.5,
                kind="transition",
                goal="Transition",
            ),
            TimelineSegment(start_seconds=3.5, end_seconds=8.0, goal="Highlight", shot_order=2),
        ],
    )

    updated = builder.apply_scene_timeline(scene, timeline)

    assert len(updated.shots) == 2


def test_build_video_timeline_without_transitions() -> None:
    builder = TimelineBuilder()
    scene = builder.finalize_scene(_scene_with_shots(duration=8.0))

    video_timeline = builder.build_video_timeline([scene], transition_duration_seconds=0.0)

    assert video_timeline.duration_seconds == 8.0
    assert all(segment.kind == "shot" for segment in video_timeline.segments)


def test_shot_durations_falls_back_to_scene_shots() -> None:
    builder = TimelineBuilder()
    scene = Scene.model_construct(
        id="scene-1",
        section_id="sec-1",
        order=0,
        goal="Explain",
        duration_seconds=8.0,
        source=SceneSource(section="Results", page=1, paragraph=1),
        shots=_scene_with_shots().shots,
        visual=SceneVisual(page=1, crop=BoundingBox(x=0, y=0, width=10, height=10)),
        timeline=None,
    )

    assert builder.shot_durations(scene) == [3.0, 3.0, 2.0]


def test_scene_timeline_requires_shot_segments() -> None:
    with pytest.raises(ValueError, match="at least one shot segment"):
        SceneTimeline(
            duration_seconds=1.0,
            segments=[
                TimelineSegment(
                    start_seconds=0.0,
                    end_seconds=1.0,
                    kind="transition",
                    goal="Transition",
                ),
            ],
        )


def test_scene_timeline_must_start_at_zero() -> None:
    with pytest.raises(ValueError, match="must start at 0 seconds"):
        SceneTimeline(
            duration_seconds=8.0,
            segments=[
                TimelineSegment(start_seconds=1.0, end_seconds=8.0, goal="Hook", shot_order=0),
            ],
        )


def test_build_video_timeline_skips_non_shot_scene_segments() -> None:
    builder = TimelineBuilder()
    scene = _scene_with_shots(duration=8.0).model_copy(
        update={
            "timeline": SceneTimeline(
                duration_seconds=8.0,
                segments=[
                    TimelineSegment(start_seconds=0.0, end_seconds=3.0, goal="Hook", shot_order=0),
                    TimelineSegment(
                        start_seconds=3.0,
                        end_seconds=3.5,
                        kind="transition",
                        goal="Transition",
                    ),
                    TimelineSegment(
                        start_seconds=3.5,
                        end_seconds=8.0,
                        goal="Highlight",
                        shot_order=2,
                    ),
                ],
            ),
        },
    )

    video_timeline = builder.build_video_timeline([scene], transition_duration_seconds=0.0)

    assert len([segment for segment in video_timeline.segments if segment.kind == "shot"]) == 2


def test_video_timeline_must_start_at_zero() -> None:
    with pytest.raises(ValueError, match="must start at 0 seconds"):
        VideoTimeline(
            duration_seconds=8.0,
            segments=[
                TimelineSegment(start_seconds=1.0, end_seconds=8.0, goal="Hook", shot_order=0),
            ],
        )
