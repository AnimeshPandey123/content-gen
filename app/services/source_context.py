"""Resolve source text from storyboard anchors for LLM prompts."""

from app.models.document import Document
from app.models.paper_brief import PaperBrief
from app.models.scene import Scene
from app.models.section import Section
from app.services.figure_detector import FigureDetector, normalize_visual_label
from app.services.screenshot_region_planner import ScreenshotRegionPlanner


def format_paper_brief(brief: PaperBrief) -> str:
    """Format a paper brief for inclusion in LLM prompts."""
    evidence_lines = "\n".join(
        f"- {point.claim}: {point.detail}"
        + (f" (from {point.source_section})" if point.source_section else "")
        for point in brief.evidence
    )
    return (
        f"Problem: {brief.problem}\n"
        f"Key insight: {brief.key_insight}\n"
        f"Mechanism: {brief.mechanism}\n"
        f"Evidence:\n{evidence_lines}\n"
        f"Limitations: {brief.limitations}\n"
        f"So what: {brief.so_what}"
    )


def find_section(sections: list[Section], title: str) -> Section | None:
    normalized_target = title.strip().casefold()
    for section in sections:
        if section.title.strip().casefold() == normalized_target:
            return section
    for section in sections:
        normalized_section = section.title.strip().casefold()
        if normalized_target in normalized_section or normalized_section in normalized_target:
            return section
    return None


def format_scene_source_context(
    document: Document,
    sections: list[Section],
    scene: Scene,
) -> str:
    """Build grounded source excerpts for one storyboard scene."""
    parts: list[str] = []
    section = find_section(sections, scene.source.section)
    if section and section.content.strip():
        parts.append(f"Section ({section.title}):\n{section.content.strip()}")

    planner = ScreenshotRegionPlanner()
    try:
        paragraph_ref = planner.get_paragraph(document, scene.source.paragraph)
        parts.append(
            f"Source paragraph {scene.source.paragraph} "
            f"(page {paragraph_ref.page_number}):\n{paragraph_ref.block.text.strip()}",
        )
    except Exception:
        pass

    visual_lines = _format_shot_visuals(document, scene)
    if visual_lines:
        parts.append(f"Referenced visuals:\n{visual_lines}")

    return "\n\n".join(parts) if parts else "(no source text available)"


def _format_shot_visuals(document: Document, scene: Scene) -> str:
    detector = FigureDetector()
    labels: list[str] = []
    seen: set[str] = set()

    for shot in scene.shots:
        if not shot.visual:
            continue
        normalized = normalize_visual_label(shot.visual)
        if normalized in seen:
            continue
        seen.add(normalized)
        visual = detector.find_visual(document, shot.visual)
        if visual is None:
            labels.append(f"- {shot.visual}: (caption not found)")
            continue
        caption = (visual.caption or "").strip() or "(no caption)"
        labels.append(f"- {visual.label} (page {visual.page_number}): {caption}")

    return "\n".join(labels)
