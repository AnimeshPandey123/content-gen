"""Time-based timeline models for scenes and the full video."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

SegmentKind = Literal["shot", "transition"]


class TimelineSegment(BaseModel):
    """A time range on the timeline with a goal and optional shot/scene reference."""

    start_seconds: float = Field(ge=0, description="Inclusive start time in seconds")
    end_seconds: float = Field(gt=0, description="Exclusive end time in seconds")
    kind: SegmentKind = Field(default="shot", description="Shot content or scene transition")
    goal: str = Field(min_length=1, description="What happens during this segment")
    shot_order: int | None = Field(
        default=None,
        ge=0,
        description="0-based shot index when kind is shot",
    )
    scene_id: str | None = Field(
        default=None,
        description="Owning scene id for video-level timelines",
    )

    @model_validator(mode="after")
    def _end_after_start(self) -> "TimelineSegment":
        if self.end_seconds <= self.start_seconds:
            raise ValueError("end_seconds must be greater than start_seconds")
        return self

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


class SceneTimeline(BaseModel):
    """Ordered shot segments covering a single scene from 0 to duration_seconds."""

    duration_seconds: float = Field(gt=0, description="Total scene runtime")
    segments: list[TimelineSegment] = Field(
        min_length=1,
        description="Shot segments covering [0, duration_seconds)",
    )

    @model_validator(mode="after")
    def _validate_coverage(self) -> "SceneTimeline":
        shot_segments = [segment for segment in self.segments if segment.kind == "shot"]
        if not shot_segments:
            raise ValueError("Scene timeline must include at least one shot segment")
        if shot_segments[0].start_seconds != 0:
            raise ValueError("Scene timeline must start at 0 seconds")
        last_end = max(segment.end_seconds for segment in shot_segments)
        if abs(last_end - self.duration_seconds) > 0.01:
            raise ValueError("Shot segments must end at the scene duration")
        return self


class VideoTimeline(BaseModel):
    """Global video timeline with scene shots and transition markers."""

    duration_seconds: float = Field(gt=0, description="Final playback duration")
    segments: list[TimelineSegment] = Field(
        min_length=1,
        description="Ordered segments across the full video",
    )

    @model_validator(mode="after")
    def _validate_starts_at_zero(self) -> "VideoTimeline":
        if self.segments[0].start_seconds != 0:
            raise ValueError("Video timeline must start at 0 seconds")
        return self
