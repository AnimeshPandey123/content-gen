"""Final video project aggregate."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from app.models.document import Document
from app.models.script import Script
from app.models.storyboard import Storyboard

if TYPE_CHECKING:
    from app.models.render import RenderProject


class VideoProject(BaseModel):
    """All artifacts required to render the final video."""

    document: Document
    storyboard: Storyboard
    script: Script
    render_project: RenderProject | None = None
    output_path: str | None = None
