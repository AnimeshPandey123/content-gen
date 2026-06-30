"""Placeholder stage implementations.

Each stage returns stub data that satisfies the data contracts.
Real PDF parsing, LLM calls, and rendering will replace these later.
"""

from app.services.stages.content_planning import ContentPlanningStage
from app.services.stages.document_extraction import DocumentExtractionStage
from app.services.stages.screenshot_generation import ScreenshotGenerationStage
from app.services.stages.script_generation import ScriptGenerationStage
from app.services.stages.semantic_parsing import SemanticParsingStage
from app.services.stages.storyboard_generation import StoryboardGenerationStage
from app.services.stages.subtitle_generation import SubtitleGenerationStage
from app.services.stages.video_rendering import VideoRenderingStage
from app.services.stages.voice_generation import VoiceGenerationStage

__all__ = [
    "ContentPlanningStage",
    "DocumentExtractionStage",
    "ScreenshotGenerationStage",
    "ScriptGenerationStage",
    "SemanticParsingStage",
    "StoryboardGenerationStage",
    "SubtitleGenerationStage",
    "VideoRenderingStage",
    "VoiceGenerationStage",
]


def build_default_stages() -> list:
    """Return the default ordered list of pipeline stages."""
    return [
        DocumentExtractionStage(),
        SemanticParsingStage(),
        ContentPlanningStage(),
        StoryboardGenerationStage(),
        ScriptGenerationStage(),
        ScreenshotGenerationStage(),
        VoiceGenerationStage(),
        SubtitleGenerationStage(),
        VideoRenderingStage(),
    ]
