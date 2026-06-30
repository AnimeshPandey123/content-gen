"""Unit tests for dynamic camera planning."""

import pytest
from app.models.bounding_box import BoundingBox
from app.models.scene import SceneShot
from app.models.storyboard_generation import PlannedScene, PlannedSceneSource, PlannedShot
from app.services.camera_planner import CameraPlanner, normalize_shot_durations
from app.services.screenshot_region_planner import ScreenshotRegionError

from tests.conftest import sample_planned_shots
from tests.test_stages import _sample_document


def test_normalize_shot_durations_returns_empty_list() -> None:
    assert normalize_shot_durations([], 6.0) == []


def test_rebalance_shot_durations_returns_empty_for_zero_total() -> None:
    planner = CameraPlanner()
    assert planner.rebalance_shot_durations([], 5.0) == []


def test_normalize_shot_durations_scales_to_scene_duration() -> None:
    shots = [
        PlannedShot(
            goal="Wide",
            duration_seconds=3.0,
            page=1,
            paragraph=1,
            framing="wide",
        ),
        PlannedShot(
            goal="Focus",
            duration_seconds=3.0,
            page=1,
            paragraph=1,
            framing="focus",
        ),
    ]

    normalized = normalize_shot_durations(shots, 6.0)

    assert sum(shot.duration_seconds for shot in normalized) == pytest.approx(6.0)


def test_resolve_shots_raises_when_llm_omits_shots() -> None:
    document = _sample_document()
    planner = CameraPlanner()
    planned = PlannedScene.model_construct(
        goal="Explain the result",
        duration_seconds=6.0,
        source=PlannedSceneSource(section="Page 1", page=1, paragraph=1),
        shots=[],
    )

    with pytest.raises(ScreenshotRegionError, match="LLM must plan each frame"):
        planner.resolve_shots(planned, document)


def test_resolve_shots_raises_when_no_shots_resolve() -> None:
    document = _sample_document()
    planner = CameraPlanner()
    planned = PlannedScene(
        goal="Explain the result",
        duration_seconds=6.0,
        source=PlannedSceneSource(section="Page 1", page=1, paragraph=1),
        shots=[
            PlannedShot(
                goal="Missing paragraph",
                duration_seconds=6.0,
                page=1,
                paragraph=99,
                framing="focus",
            ),
        ],
    )

    with pytest.raises(ScreenshotRegionError, match="No camera shots could be resolved"):
        planner.resolve_shots(planned, document)


def test_resolve_shots_skips_unresolvable_shots() -> None:
    document = _sample_document()
    planner = CameraPlanner()
    planned = PlannedScene(
        goal="Explain the result",
        duration_seconds=6.0,
        source=PlannedSceneSource(section="Page 1", page=1, paragraph=1),
        shots=[
            PlannedShot(
                goal="Missing paragraph",
                duration_seconds=2.0,
                page=1,
                paragraph=99,
                framing="focus",
            ),
            PlannedShot(
                goal="Valid wide shot",
                duration_seconds=4.0,
                page=1,
                paragraph=1,
                framing="wide",
            ),
        ],
    )

    shots = planner.resolve_shots(planned, document)

    assert len(shots) == 1
    assert shots[0].framing == "wide"


def test_resolve_shots_uses_llm_planned_shots() -> None:
    document = _sample_document()
    planner = CameraPlanner()
    planned = PlannedScene(
        goal="Explain the result",
        duration_seconds=6.0,
        source=PlannedSceneSource(section="Page 1", page=1, paragraph=1),
        shots=[
            PlannedShot(
                goal="Show the full figure",
                duration_seconds=2.0,
                page=1,
                paragraph=1,
                framing="wide",
            ),
            PlannedShot(
                goal="Zoom the graph",
                duration_seconds=2.5,
                page=1,
                paragraph=1,
                framing="focus",
            ),
            PlannedShot(
                goal="Highlight the result",
                duration_seconds=1.5,
                page=1,
                paragraph=1,
                framing="highlight",
            ),
        ],
    )

    shots = planner.resolve_shots(planned, document)

    assert [shot.goal for shot in shots] == [
        "Show the full figure",
        "Zoom the graph",
        "Highlight the result",
    ]


def test_resolve_shots_uses_visual_reference() -> None:
    from tests.test_figure_detector import _document_with_visuals

    document = _document_with_visuals()
    planner = CameraPlanner()
    planned = PlannedScene(
        goal="Explain the architecture",
        duration_seconds=5.0,
        source=PlannedSceneSource(section="Page 1", page=1, paragraph=1),
        shots=[
            PlannedShot(
                goal="Show the model diagram",
                duration_seconds=5.0,
                visual="Figure 1",
            ),
        ],
    )

    shots = planner.resolve_shots(planned, document)

    assert len(shots) == 1
    assert shots[0].visual == "Figure 1"
    assert shots[0].page == 1


def test_rebalance_shot_durations_updates_scene_shots() -> None:
    planner = CameraPlanner()
    shots = [
        SceneShot(
            order=0,
            goal="A",
            duration_seconds=2.0,
            page=1,
            paragraph=1,
            framing="wide",
            crop=BoundingBox(x=0, y=0, width=10, height=10),
        ),
        SceneShot(
            order=1,
            goal="B",
            duration_seconds=2.0,
            page=1,
            paragraph=1,
            framing="focus",
            crop=BoundingBox(x=0, y=0, width=10, height=10),
        ),
    ]

    rebalanced = planner.rebalance_shot_durations(shots, 5.0)

    assert sum(shot.duration_seconds for shot in rebalanced) == pytest.approx(5.0)
