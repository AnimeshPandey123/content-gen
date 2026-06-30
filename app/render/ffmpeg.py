"""FFmpeg helpers for scene rendering and concatenation."""

import subprocess
import textwrap
from pathlib import Path

from app.config import Settings, get_settings
from app.render.camera import build_video_filter


class FFmpegError(Exception):
    """Raised when FFmpeg fails."""


class FFmpegRenderer:
    """Render scene clips and concatenate them into a final MP4."""

    def __init__(self, *, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def render_scene(
        self,
        *,
        image_path: str,
        audio_path: str,
        subtitle_path: str,
        output_path: Path,
        duration_seconds: float,
    ) -> None:
        """Render one scene clip with camera motion, subtitles, and narration."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        video_filter = build_video_filter(
            motion=self._settings.camera_motion,
            width=self._settings.video_width,
            height=self._settings.video_height,
            fps=self._settings.video_fps,
            duration_seconds=duration_seconds,
            ass_path=subtitle_path,
        )
        args = [
            "-y",
            "-loop",
            "1",
            "-i",
            image_path,
            "-i",
            audio_path,
            "-vf",
            video_filter,
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-t",
            f"{duration_seconds:.3f}",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]
        self._run(args)

    def concat_clips(self, clip_paths: list[Path], output_path: Path) -> None:
        """Concatenate rendered scene clips into the final video."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        concat_file = output_path.parent / "concat_list.txt"
        lines = [f"file '{path.resolve().as_posix()}'" for path in clip_paths]
        concat_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        args = [
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            str(output_path),
        ]
        self._run(args)

    def _run(self, args: list[str]) -> None:
        command = [self._settings.ffmpeg_path, *args]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise FFmpegError(f"FFmpeg not found: {self._settings.ffmpeg_path}") from exc

        if result.returncode != 0:
            stderr = textwrap.shorten(result.stderr or "ffmpeg failed", width=300)
            raise FFmpegError(stderr)
