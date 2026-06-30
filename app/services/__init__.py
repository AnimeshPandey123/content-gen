"""Placeholder stage implementations.

Each stage returns stub data that satisfies the data contracts.
Real PDF parsing, LLM calls, and rendering will replace these later.
"""

from app.services.stages.caption_generation import CaptionGenerationStage
from app.services.stages.content_planning import ContentPlanningStage
from app.services.stages.document_extraction import DocumentExtractionStage
from app.services.stages.narration_generation import NarrationGenerationStage
from app.services.stages.screenshot_planning import ScreenshotPlanningStage
from app.services.stages.storyboard_generation import StoryboardGenerationStage
from app.services.stages.video_rendering import VideoRenderingStage

__all__ = [
    "CaptionGenerationStage",
    "ContentPlanningStage",
    "DocumentExtractionStage",
    "NarrationGenerationStage",
    "ScreenshotPlanningStage",
    "StoryboardGenerationStage",
    "VideoRenderingStage",
]


def build_default_stages() -> list:
    """Return the default ordered list of pipeline stages."""
    return [
        DocumentExtractionStage(),
        ContentPlanningStage(),
        StoryboardGenerationStage(),
        ScreenshotPlanningStage(),
        NarrationGenerationStage(),
        CaptionGenerationStage(),
        VideoRenderingStage(),
    ]
