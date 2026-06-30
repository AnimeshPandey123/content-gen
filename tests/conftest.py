"""Shared test fixtures."""

from pathlib import Path

import fitz
import pytest
from app.config import reset_settings
from app.models.bounding_box import BoundingBox
from app.models.scene import Scene, SceneShot, SceneSource, SceneVisual
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


def sample_planned_shots(
    *,
    duration: float = 5.0,
    page: int = 1,
    paragraph: int = 1,
):
    """Return a typical LLM-planned two-shot sequence for tests."""
    from app.models.storyboard_generation import PlannedShot

    wide_duration = round(duration * 0.4, 3)
    focus_duration = round(duration - wide_duration, 3)
    return [
        PlannedShot(
            goal="Show context",
            duration_seconds=wide_duration,
            page=page,
            paragraph=paragraph,
            framing="wide",
        ),
        PlannedShot(
            goal="Focus on the key detail",
            duration_seconds=focus_duration,
            page=page,
            paragraph=paragraph,
            framing="focus",
        ),
    ]


def sample_video_plan(**overrides):
    """Return a typical LLM video pacing plan for tests."""
    from app.models.video_plan import VideoPlan

    values = {
        "target_video_duration_seconds": 30.0,
        "title_page_duration_seconds": 4.0,
        "min_scene_duration_seconds": 3.0,
    }
    values.update(overrides)
    return VideoPlan(**values)


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
        planner = ScreenshotRegionPlanner()
        title_crop = planner.crop_for_page(content_plan.document, 1)
        page_number, content_crop = planner.crop_for_paragraph(
            content_plan.document,
            paragraph_index,
        )
        return Storyboard(
            document_id=content_plan.document.id,
            scenes=[
                Scene(
                    id=f"{content_plan.document.id}-scene-intro",
                    section_id=section.id,
                    order=0,
                    goal="Show the paper title page",
                    duration_seconds=4.0,
                    source=SceneSource(
                        section=section.title,
                        page=1,
                        paragraph=1,
                    ),
                    shots=[
                        SceneShot(
                            order=0,
                            goal="Show the paper title page",
                            duration_seconds=4.0,
                            page=1,
                            paragraph=1,
                            framing="wide",
                            crop=title_crop,
                        ),
                    ],
                    visual=SceneVisual(page=1, crop=title_crop),
                ),
                Scene(
                    id=f"{content_plan.document.id}-scene-1",
                    section_id=section.id,
                    order=1,
                    goal=f"Introduce {section.title}",
                    duration_seconds=8.0,
                    source=SceneSource(
                        section=section.title,
                        page=page_number,
                        paragraph=paragraph_index,
                    ),
                    shots=[
                        SceneShot(
                            order=0,
                            goal=f"Introduce {section.title}",
                            duration_seconds=8.0,
                            page=page_number,
                            paragraph=paragraph_index,
                            framing="focus",
                            crop=content_crop,
                        ),
                    ],
                    visual=SceneVisual(page=page_number, crop=content_crop),
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


def mock_render_stages(monkeypatch, tmp_path) -> None:
    """Bypass FFmpeg and heavy asset generation during integration tests."""
    from pathlib import Path

    from app.models.render import SceneAudio, SceneScreenshot, SceneSubtitle
    from app.render.assembler import VideoAssembler
    from app.render.project import (
        audio_path,
        clip_path,
        final_video_path,
        shot_screenshot_path,
        subtitle_path,
    )
    from app.render.screenshot import ScreenshotGenerator
    from app.render.subtitles import SubtitleGenerator
    from app.render.voice import VoiceGenerator

    def _fake_screenshots(self, project):
        project_dir = Path(project.project_dir)
        screenshots: list[SceneScreenshot] = []
        for scene_asset in project.scenes:
            storyboard_scene = next(
                item
                for item in project.script_plan.storyboard_result.storyboard.scenes
                if item.id == scene_asset.scene_id
            )
            for shot in storyboard_scene.shots:
                path = shot_screenshot_path(project_dir, scene_asset.scene_number, shot.order)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"png")
                screenshots.append(
                    SceneScreenshot(
                        scene_id=scene_asset.scene_id,
                        shot_order=shot.order,
                        image_path=str(path),
                    ),
                )
        return screenshots

    def _fake_voice(self, project):
        project_dir = Path(project.project_dir)
        audio_files: list[SceneAudio] = []
        for scene_asset in project.scenes:
            script_scene = next(
                item
                for item in project.script_plan.script.scenes
                if item.scene_id == scene_asset.scene_id
            )
            path = audio_path(project_dir, scene_asset.scene_number)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"wav")
            audio_files.append(
                SceneAudio(
                    scene_id=scene_asset.scene_id,
                    audio_path=str(path),
                    duration_seconds=script_scene.duration,
                ),
            )
        return audio_files

    def _fake_subtitles(self, project, audio_files):
        project_dir = Path(project.project_dir)
        subtitles: list[SceneSubtitle] = []
        for scene_asset in project.scenes:
            path = subtitle_path(project_dir, scene_asset.scene_number)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("ass", encoding="utf-8")
            subtitles.append(SceneSubtitle(scene_id=scene_asset.scene_id, subtitle_path=str(path)))
        return subtitles

    def _fake_assemble(self, project):
        project_dir = Path(project.project_dir)
        document_id = project.script_plan.storyboard_result.content_plan.document.id
        clips = []
        for scene_asset in project.scenes:
            path = clip_path(project_dir, scene_asset.scene_number)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("clip", encoding="utf-8")
            from app.models.render import SceneClip

            clips.append(SceneClip(scene_id=scene_asset.scene_id, clip_path=str(path)))
        video_path = final_video_path(project_dir, document_id)
        video_path.write_text("video", encoding="utf-8")
        return project.with_clips(clips).with_video_path(str(video_path))

    monkeypatch.setattr(ScreenshotGenerator, "produce", _fake_screenshots)
    monkeypatch.setattr(VoiceGenerator, "produce", _fake_voice)
    monkeypatch.setattr(SubtitleGenerator, "produce", _fake_subtitles)
    monkeypatch.setattr(VideoAssembler, "render", _fake_assemble)


@pytest.fixture(autouse=True)
def _reset_settings() -> None:
    reset_settings()
    yield
    reset_settings()
