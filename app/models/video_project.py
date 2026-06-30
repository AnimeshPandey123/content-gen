"""Final video project aggregate."""

from pydantic import BaseModel

from app.models.document import Document
from app.models.script import Script
from app.models.storyboard import Storyboard


class VideoProject(BaseModel):
    """All artifacts required to render the final video."""

    document: Document
    storyboard: Storyboard
    script: Script
    output_path: str | None = None
