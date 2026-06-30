"""Crop high-resolution screenshots from PDF storyboard regions."""

from pathlib import Path

import fitz

from app.config import Settings, get_settings
from app.models.bounding_box import BoundingBox
from app.models.render import RenderProject, SceneScreenshot
from app.render.project import screenshot_path


class ScreenshotGeneratorError(Exception):
    """Raised when a screenshot cannot be generated."""


class ScreenshotGenerator:
    """Feature 8: render PDF page crops as reusable PNG assets."""

    def __init__(self, *, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def produce(self, project: RenderProject) -> list[SceneScreenshot]:
        document = project.script_plan.storyboard_result.content_plan.document
        project_dir = Path(project.project_dir)
        screenshots_dir = project_dir / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        screenshots: list[SceneScreenshot] = []
        for scene in project.script_plan.storyboard_result.storyboard.scenes:
            image_path = screenshot_path(project_dir, scene.order + 1)
            self.render_crop(
                pdf_path=document.source_path,
                page_number=scene.visual.page,
                crop=scene.visual.crop,
                output_path=image_path,
            )
            screenshots.append(
                SceneScreenshot(scene_id=scene.id, image_path=str(image_path.resolve())),
            )

        return screenshots

    def render_crop(
        self,
        *,
        pdf_path: str,
        page_number: int,
        crop: BoundingBox,
        output_path: Path,
    ) -> None:
        """Render a PDF crop region to a PNG at screenshot DPI."""
        path = Path(pdf_path)
        if not path.is_file():
            raise ScreenshotGeneratorError(f"PDF file not found: {path}")

        try:
            pdf = fitz.open(path)
        except Exception as exc:
            raise ScreenshotGeneratorError(f"Failed to open PDF: {path}") from exc

        try:
            if page_number < 1 or page_number > pdf.page_count:
                raise ScreenshotGeneratorError(f"Page {page_number} not found in PDF")

            page = pdf[page_number - 1]
            zoom = self._settings.screenshot_dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)
            clip = fitz.Rect(crop.x, crop.y, crop.x + crop.width, crop.y + crop.height)
            pixmap = page.get_pixmap(matrix=matrix, clip=clip, alpha=False)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            pixmap.save(str(output_path))
        finally:
            pdf.close()
