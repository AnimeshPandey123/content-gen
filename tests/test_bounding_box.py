"""Unit tests for bounding box helpers."""

import pytest
from app.models.bounding_box import BoundingBox, intersect_bbox, merge_crop_for_continuity


def test_intersect_bbox_returns_overlap() -> None:
    left = BoundingBox(x=10, y=10, width=50, height=50)
    right = BoundingBox(x=40, y=40, width=50, height=50)

    overlap = intersect_bbox(left, right)

    assert overlap == BoundingBox(x=40, y=40, width=20, height=20)


def test_intersect_bbox_returns_none_when_disjoint() -> None:
    left = BoundingBox(x=0, y=0, width=10, height=10)
    right = BoundingBox(x=20, y=20, width=10, height=10)

    assert intersect_bbox(left, right) is None


def test_merge_crop_for_continuity_expands_tall_follow_up_shot_to_page_top() -> None:
    previous = BoundingBox(x=0.0, y=0.0, width=612.0, height=792.0)
    current = BoundingBox(x=0.0, y=118.0, width=612.0, height=673.0)

    merged = merge_crop_for_continuity(previous, current, page_height=792.0)

    assert merged.y == 0.0
    assert merged.height == pytest.approx(728.64, rel=0.01)


def test_merge_crop_for_continuity_keeps_small_crops_separate() -> None:
    previous = BoundingBox(x=0.0, y=0.0, width=612.0, height=200.0)
    current = BoundingBox(x=0.0, y=300.0, width=612.0, height=180.0)

    merged = merge_crop_for_continuity(previous, current, page_height=792.0)

    assert merged.y == 0.0
    assert merged.height == 480.0
