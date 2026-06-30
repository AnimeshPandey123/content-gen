"""Shared test fixtures."""

from pathlib import Path

import fitz
import pytest
from app.config import reset_settings
from app.models.bounding_box import BoundingBox
from app.models.scene import Scene, SceneSource, SceneVisual
from app.services.screenshot_region_planner import ScreenshotRegionPlanner


def write_sample_pdf(
    path: Path,
    *,
    pages: list[str] | None = None,
    title: str | None = None,
) -> Path:
    """Create a minimal PDF file for tests."""
    page_texts = pages or ["Hello PDF"]
    doc = fitz.open()
    if title:
        doc.set_metadata({"title": title})

    for text in page_texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)

    doc.save(path)
    doc.close()
    return path


def write_semantic_pdf(path: Path) -> Path:
    """Create a PDF with headings, paragraphs, and a caption-like line."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Introduction", fontsize=18)
    page.insert_text(
        (72, 110),
        "This is the opening paragraph of the document.",
        fontsize=11,
    )
    page.insert_text((72, 150), "Figure 1: Example diagram.", fontsize=10)
    doc.save(path)
    doc.close()
    return path


def sample_scene(**overrides) -> Scene:
    values = {
        "id": "scene-1",
        "section_id": "sec-1",
        "order": 0,
        "goal": "Scene",
        "duration_seconds": 4.0,
        "source": SceneSource(section="Highlight", page=1, paragraph=1),
        "visual": SceneVisual(page=1, crop=BoundingBox(x=72.0, y=72.0, width=400.0, height=18.0)),
    }
    values.update(overrides)
    return Scene(**values)


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    return write_sample_pdf(
        tmp_path / "paper.pdf",
        pages=["Page one content.", "Page two content."],
        title="Sample Paper",
    )


@pytest.fixture
def semantic_pdf(tmp_path: Path) -> Path:
    return write_semantic_pdf(tmp_path / "semantic.pdf")


def mock_section_selection(monkeypatch) -> None:
    """Bypass Gemini during integration tests."""
    from app.models.section import Section
    from app.services.section_selector import SectionSelector

    def _fake_select(self, document):
        refs = list(ScreenshotRegionPlanner().iter_paragraphs(document))
        paragraph_indices = [refs[0].index] if refs else []
        return [
            Section(
                id=f"{document.id}-section-1",
                title="Highlight",
                content=document.raw_text[:500] or document.pages[0].text,
                page_numbers=[document.pages[0].page_number],
                paragraph_indices=paragraph_indices,
                importance_score=0.9,
            ),
        ]

    monkeypatch.setattr(SectionSelector, "select_sections", _fake_select)


def mock_storyboard_generation(monkeypatch) -> None:
    """Bypass Gemini during integration tests."""
    from app.models.storyboard import Storyboard
    from app.services.storyboard_generator import StoryboardGenerator

    def _fake_generate(self, content_plan):
        section = content_plan.selected_sections[0]
        paragraph_index = section.paragraph_indices[0] if section.paragraph_indices else 1
        page_number, crop = ScreenshotRegionPlanner().crop_for_paragraph(
            content_plan.document,
            paragraph_index,
        )
        return Storyboard(
            document_id=content_plan.document.id,
            scenes=[
                Scene(
                    id=f"{content_plan.document.id}-scene-1",
                    section_id=section.id,
                    order=0,
                    goal=f"Introduce {section.title}",
                    duration_seconds=8.0,
                    source=SceneSource(
                        section=section.title,
                        page=page_number,
                        paragraph=paragraph_index,
                    ),
                    visual=SceneVisual(page=page_number, crop=crop),
                ),
            ],
        )

    monkeypatch.setattr(StoryboardGenerator, "generate_storyboard", _fake_generate)


def mock_script_generation(monkeypatch) -> None:
    """Bypass Gemini during integration tests."""
    from app.models.script import Script, ScriptScene
    from app.services.script_generator import ScriptGenerator

    def _fake_generate(self, storyboard_result):
        return Script(
            scenes=[
                ScriptScene(
                    scene=scene.order + 1,
                    scene_id=scene.id,
                    voice=f"Voice for scene {scene.order + 1}",
                    overlay=scene.goal,
                    duration=scene.duration_seconds,
                )
                for scene in storyboard_result.storyboard.scenes
            ],
        )

    monkeypatch.setattr(ScriptGenerator, "generate_script", _fake_generate)


def mock_render_pipeline(monkeypatch, tmp_path) -> None:
    """Bypass FFmpeg during integration tests."""
    from app.models.render import (
        RenderArtifacts,
        SceneAudio,
        SceneClip,
        SceneScreenshot,
        SceneSubtitle,
    )
    from app.render.pipeline import RenderPipeline

    def _fake_run(self, script_plan):
        document_id = script_plan.storyboard_result.content_plan.document.id
        project_dir = tmp_path / document_id
        project_dir.mkdir(parents=True, exist_ok=True)
        video_path = project_dir / f"{document_id}.mp4"
        video_path.write_text("video", encoding="utf-8")
        scene_id = script_plan.script.scenes[0].scene_id
        return RenderArtifacts(
            project_dir=str(project_dir),
            screenshots=[
                SceneScreenshot(scene_id=scene_id, image_path=str(project_dir / "s.png")),
            ],
            audio_files=[
                SceneAudio(
                    scene_id=scene_id,
                    audio_path=str(project_dir / "a.wav"),
                    duration_seconds=5.0,
                ),
            ],
            subtitle_files=[
                SceneSubtitle(scene_id=scene_id, subtitle_path=str(project_dir / "s.ass")),
            ],
            scene_clips=[SceneClip(scene_id=scene_id, clip_path=str(project_dir / "c.mp4"))],
            video_path=str(video_path),
        )

    monkeypatch.setattr(RenderPipeline, "run", _fake_run)


@pytest.fixture(autouse=True)
def _reset_settings() -> None:
    reset_settings()
    yield
    reset_settings()
