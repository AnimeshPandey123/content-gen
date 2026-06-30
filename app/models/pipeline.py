"""Pipeline input/output models that connect workflow stages."""

from pydantic import BaseModel, Field

from app.models.caption import Caption
from app.models.document import Document
from app.models.narration import Narration
from app.models.screenshot import ScreenshotRegion
from app.models.section import Section
from app.models.storyboard import Storyboard
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


class ScreenshotPlan(BaseModel):
    """Planned screenshot regions for each scene."""

    storyboard_result: StoryboardResult
    regions: list[ScreenshotRegion] = Field(min_length=1)


class NarrationPlan(BaseModel):
    """Generated narration scripts per scene."""

    screenshot_plan: ScreenshotPlan
    narrations: list[Narration] = Field(min_length=1)


class CaptionPlan(BaseModel):
    """Generated captions aligned to narration."""

    narration_plan: NarrationPlan
    captions: list[Caption] = Field(min_length=1)


class RenderResult(BaseModel):
    """Final output of the rendering stage."""

    project: VideoProject
    video_path: str
    success: bool = True
