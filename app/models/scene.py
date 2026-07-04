"""Storyboard scene model."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models.bounding_box import BoundingBox
from app.models.timeline import SceneTimeline

CameraFraming = Literal["wide", "focus", "highlight"]


class SceneSource(BaseModel):
    """Where a scene draws its content from in the document."""

    section: str = Field(min_length=1, description="Section title")
    page: int = Field(ge=1, description="1-based PDF page number")
    paragraph: int = Field(ge=1, description="1-based paragraph index")


class SceneVisual(BaseModel):
    """Visual framing for a scene."""

    page: int = Field(ge=1, description="1-based PDF page number")
    crop: BoundingBox = Field(description="PDF crop region in page coordinates")


class SceneShot(BaseModel):
    """A single camera moment within a storyboard scene."""

    order: int = Field(ge=0, description="0-based order within the scene")
    goal: str = Field(min_length=1, description="What this camera shot should show")
    start_seconds: float = Field(
        ge=0,
        default=0,
        description="Scene-relative start time in seconds",
    )
    end_seconds: float | None = Field(
        default=None,
        gt=0,
        description="Scene-relative end time in seconds",
    )
    duration_seconds: float = Field(gt=0, description="On-screen duration for this shot")
    page: int = Field(ge=1, description="1-based PDF page number")
    paragraph: int = Field(ge=1, description="1-based paragraph index")
    visual: str | None = Field(
        default=None,
        description='Resolved figure or table label when the shot targets a detected visual',
    )
    framing: CameraFraming = Field(
        default="focus",
        description="Camera framing: wide, focus, or highlight",
    )
    crop: BoundingBox = Field(description="PDF crop region in page coordinates")
    marker_highlight: bool = Field(
        default=False,
        description="Draw a marker highlight on the paragraph or visual bbox during this shot",
    )


class Scene(BaseModel):
    """A single scene in the video storyboard."""

    id: str
    section_id: str
    order: int = Field(ge=0)
    goal: str = Field(min_length=1, description="What this scene should communicate")
    duration_seconds: float = Field(gt=0, description="Target on-screen duration")
    source: SceneSource
    shots: list[SceneShot] = Field(
        min_length=1,
        description="Ordered camera shots that play during this scene",
    )
    visual: SceneVisual = Field(description="Primary visual (first shot) for compatibility")
    timeline: SceneTimeline | None = Field(
        default=None,
        description="Absolute shot timeline for this scene",
    )

    @model_validator(mode="before")
    @classmethod
    def _ensure_shots_from_legacy_visual(cls, data):
        if not isinstance(data, dict):
            return data
        if data.get("shots"):
            return data
        visual = data.get("visual")
        if visual is None:
            return data
        page = visual["page"] if isinstance(visual, dict) else visual.page
        crop = visual["crop"] if isinstance(visual, dict) else visual.crop
        duration = data.get("duration_seconds", 1.0)
        goal = data.get("goal", "Scene")
        source = data.get("source")
        if isinstance(source, dict):
            paragraph = source.get("paragraph", 1)
        else:
            paragraph = source.paragraph
        data["shots"] = [
            {
                "order": 0,
                "goal": goal,
                "duration_seconds": duration,
                "page": page,
                "paragraph": paragraph,
                "framing": "focus",
                "crop": crop,
            },
        ]
        return data

    @model_validator(mode="after")
    def _sync_visual_from_first_shot(self):
        first_shot = self.shots[0]
        visual = SceneVisual(page=first_shot.page, crop=first_shot.crop)
        if self.visual.page != visual.page or self.visual.crop != visual.crop:
            object.__setattr__(self, "visual", visual)
        return self

    @model_validator(mode="after")
    def _ensure_timeline(self):
        if self.timeline is not None:
            return self
        from app.services.timeline_builder import TimelineBuilder

        finalized = TimelineBuilder().finalize_scene(self)
        object.__setattr__(self, "timeline", finalized.timeline)
        object.__setattr__(self, "shots", finalized.shots)
        return self
