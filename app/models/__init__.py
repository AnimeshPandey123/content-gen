"""Domain models for the PDF-to-video pipeline."""

from app.models.blocks import (
    Caption as SemanticCaption,
)
from app.models.blocks import (
    Figure,
    Heading,
    Paragraph,
    SemanticBlock,
    Table,
    text_from_blocks,
)
from app.models.bounding_box import BoundingBox
from app.models.caption import Caption
from app.models.document import Document
from app.models.metadata import DocumentMetadata
from app.models.narration import Narration
from app.models.page import Page
from app.models.pipeline import (
    ContentPlan,
    PipelineInput,
    RenderResult,
    ScriptPlan,
    StoryboardResult,
)
from app.models.render import (
    RenderProject,
    SceneAssets,
    SceneAudio,
    SceneClip,
    SceneScreenshot,
    SceneSubtitle,
)
from app.models.scene import Scene, SceneShot, SceneSource, SceneVisual
from app.models.screenshot import ScreenshotRegion
from app.models.script import Script, ScriptScene
from app.models.section import Section
from app.models.storyboard import Storyboard
from app.models.video_project import VideoProject

RenderProject.model_rebuild()
VideoProject.model_rebuild()
RenderResult.model_rebuild()

__all__ = [
    "BoundingBox",
    "Caption",
    "ContentPlan",
    "Document",
    "DocumentMetadata",
    "Figure",
    "Heading",
    "Narration",
    "Page",
    "Paragraph",
    "PipelineInput",
    "RenderProject",
    "RenderResult",
    "Scene",
    "SceneAssets",
    "SceneAudio",
    "SceneClip",
    "SceneScreenshot",
    "SceneShot",
    "SceneSource",
    "SceneSubtitle",
    "SceneVisual",
    "Script",
    "ScriptPlan",
    "ScriptScene",
    "SemanticBlock",
    "SemanticCaption",
    "ScreenshotRegion",
    "Section",
    "Storyboard",
    "StoryboardResult",
    "Table",
    "VideoProject",
    "text_from_blocks",
]
