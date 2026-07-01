"""Unit tests for screenshot asset generation."""

from pathlib import Path

import fitz
import pytest
from app.config import Settings
from app.models.bounding_box import BoundingBox
from app.models.pipeline import ContentPlan, ScriptPlan, StoryboardResult
from app.models.scene import Scene, SceneSource, SceneVisual
from app.models.section import Section
from app.models.storyboard import Storyboard
from app.render.project import bootstrap_render_project
from app.render.screenshot import ScreenshotGenerator, ScreenshotGeneratorError
from app.services.stages.screenshot_generation import ScreenshotGenerationStage


def _script_plan(pdf_path: Path) -> ScriptPlan:
    from app.models.document import Document
    from app.models.metadata import DocumentMetadata
    from app.models.page import Page
    from app.models.script import Script, ScriptScene, ScriptShot

    document = Document(
        id="doc-1",
        source_path=str(pdf_path),
        metadata=DocumentMetadata(page_count=1),
        pages=[Page(page_number=1, width=612, height=792)],
    )
    scene = Scene(
        id="scene-1",
        section_id="sec-1",
        order=0,
        goal="Intro",
        duration_seconds=5.0,
        source=SceneSource(section="Intro", page=1, paragraph=1),
        visual=SceneVisual(page=1, crop=BoundingBox(x=72, y=72, width=200, height=40)),
    )
    return ScriptPlan(
        storyboard_result=StoryboardResult(
            content_plan=ContentPlan(
                document=document,
                selected_sections=[
                    Section(id="sec-1", title="Intro", content="Hello", page_numbers=[1]),
                ],
            ),
            storyboard=Storyboard(document_id="doc-1", scenes=[scene]),
        ),
        script=Script(
            scenes=[
                ScriptScene(
                    scene=1,
                    scene_id="scene-1",
                    shots=[
                        ScriptShot(shot_order=0, voice="Hello world", overlay="Hello"),
                    ],
                ),
            ],
        ),
    )


def test_render_crop_writes_scene01_png(tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Crop this paragraph.")
    doc.save(pdf_path)
    doc.close()

    script_plan = _script_plan(pdf_path)
    project = bootstrap_render_project(script_plan, settings=Settings(output_dir=tmp_path))
    generator = ScreenshotGenerator(settings=Settings(output_dir=tmp_path, screenshot_dpi=150))
    screenshots = generator.produce(project)

    assert screenshots[0].image_path.endswith("scene01_shot01.png")
    assert Path(screenshots[0].image_path).exists()


def test_screenshot_generation_stage_bootstraps_project(tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Crop this paragraph.")
    doc.save(pdf_path)
    doc.close()

    stage = ScreenshotGenerationStage(settings=Settings(output_dir=tmp_path, screenshot_dpi=150))
    project = stage.run(_script_plan(pdf_path))

    assert Path(project.storyboard_path).exists()
    assert project.scenes[0].screenshot_path is not None


def test_render_crop_raises_for_missing_pdf(tmp_path: Path) -> None:
    generator = ScreenshotGenerator(settings=Settings(output_dir=tmp_path))

    with pytest.raises(ScreenshotGeneratorError, match="not found"):
        generator.render_crop(
            pdf_path=str(tmp_path / "missing.pdf"),
            page_number=1,
            crop=BoundingBox(x=0, y=0, width=10, height=10),
            output_path=tmp_path / "out.png",
        )


def test_render_crop_raises_for_invalid_pdf(tmp_path: Path) -> None:
    bad_pdf = tmp_path / "bad.pdf"
    bad_pdf.write_bytes(b"not a pdf")
    generator = ScreenshotGenerator(settings=Settings(output_dir=tmp_path))

    with pytest.raises(ScreenshotGeneratorError, match="Failed to open PDF"):
        generator.render_crop(
            pdf_path=str(bad_pdf),
            page_number=1,
            crop=BoundingBox(x=0, y=0, width=10, height=10),
            output_path=tmp_path / "out.png",
        )


def test_render_crop_raises_for_invalid_page(tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(pdf_path)
    doc.close()

    generator = ScreenshotGenerator(settings=Settings(output_dir=tmp_path))

    with pytest.raises(ScreenshotGeneratorError, match="Page 9 not found"):
        generator.render_crop(
            pdf_path=str(pdf_path),
            page_number=9,
            crop=BoundingBox(x=0, y=0, width=10, height=10),
            output_path=tmp_path / "out.png",
        )
