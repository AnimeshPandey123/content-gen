"""Pipeline input/output models that connect workflow stages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from app.models.document import Document
from app.models.script import Script
from app.models.section import Section
from app.models.storyboard import Storyboard

if TYPE_CHECKING:
    from app.models.render import RenderProject
    from app.models.video_project import VideoProject


class PipelineInput(BaseModel):
    """Initial input to the pipeline."""

    pdf_path: str = Field(min_length=1)
    project_id: str | None = None


class ContentPlan(BaseModel):
    """Output of content planning: document with selected sections."""

    document: Document
    selected_sections: list[Section] = Field(min_length=1)


class StoryboardResult(BaseModel):
    """Storyboard paired with its source content plan."""

    content_plan: ContentPlan
    storyboard: Storyboard


class ScriptPlan(BaseModel):
    """Generated script paired with its storyboard."""

    storyboard_result: StoryboardResult
    script: Script


class RenderResult(BaseModel):
    """Final output of the rendering stage."""

    project: VideoProject
    video_path: str
    render_project: RenderProject
    success: bool = True
