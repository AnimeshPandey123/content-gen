"""Shared test fixtures."""

from pathlib import Path

import fitz
import pytest
from app.config import reset_settings


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
    from app.services.screenshot_region_planner import ScreenshotRegionPlanner
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
    from app.models.scene import Scene
    from app.models.storyboard import Storyboard
    from app.services.storyboard_generator import StoryboardGenerator

    def _fake_generate(self, content_plan):
        section = content_plan.selected_sections[0]
        paragraph_index = section.paragraph_indices[0] if section.paragraph_indices else 1
        return Storyboard(
            document_id=content_plan.document.id,
            scenes=[
                Scene(
                    id=f"{content_plan.document.id}-scene-1",
                    section_id=section.id,
                    order=0,
                    goal=f"Visual summary of {section.title}",
                    duration_seconds=5.0,
                    source=section.title,
                    screenshot=f"Paragraph {paragraph_index}",
                    narration=f"Here is a quick look at {section.title}.",
                    caption=section.title,
                    paragraph_index=paragraph_index,
                ),
            ],
        )

    monkeypatch.setattr(StoryboardGenerator, "generate_storyboard", _fake_generate)


@pytest.fixture(autouse=True)
def _reset_settings() -> None:
    reset_settings()
    yield
    reset_settings()
