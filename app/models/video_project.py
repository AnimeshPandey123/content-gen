"""Final video project aggregate."""

from pydantic import BaseModel

from app.models.caption import Caption
from app.models.document import Document
from app.models.narration import Narration
from app.models.screenshot import ScreenshotRegion
from app.models.storyboard import Storyboard


class VideoProject(BaseModel):
    """All artifacts required to render the final video."""

    document: Document
    storyboard: Storyboard
    screenshot_regions: list[ScreenshotRegion]
    narrations: list[Narration]
    captions: list[Caption]
    output_path: str | None = None
