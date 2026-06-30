"""FFmpeg helpers for scene rendering and concatenation."""

import json
import subprocess
from pathlib import Path

from app.config import Settings, get_settings
from app.render.camera import (
    build_clip_transition_filter,
    build_multi_shot_video_filter,
    build_video_filter,
)


class FFmpegError(Exception):
    """Raised when FFmpeg fails."""


class FFmpegRenderer:
    """Render scene clips and concatenate them into a final MP4."""

    def __init__(self, *, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def render_scene(
        self,
        *,
        image_paths: list[str],
        shot_durations: list[float],
        audio_path: str,
        subtitle_path: str,
        output_path: Path,
        duration_seconds: float | None = None,
    ) -> None:
        """Render one scene clip from one or more camera shots plus narration."""
        from app.render.audio import probe_wav_duration

        if not image_paths:
            raise FFmpegError("At least one screenshot is required to render a scene")
        if len(image_paths) != len(shot_durations):
            raise FFmpegError("Each screenshot must have a matching shot duration")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        audio_duration = duration_seconds or probe_wav_duration(Path(audio_path))

        if len(image_paths) == 1:
            self._render_single_shot_scene(
                image_path=image_paths[0],
                audio_path=audio_path,
                subtitle_path=subtitle_path,
                output_path=output_path,
                duration_seconds=audio_duration,
            )
            return

        scaled_durations = self._scale_shot_durations(shot_durations, audio_duration)
        filter_complex, video_output = build_multi_shot_video_filter(
            shot_count=len(image_paths),
            motion=self._settings.camera_motion,
            width=self._settings.video_width,
            height=self._settings.video_height,
            fps=self._settings.video_fps,
            ass_path=subtitle_path,
        )
        args = ["-y"]
        for image_path, shot_duration in zip(image_paths, scaled_durations, strict=True):
            args.extend(["-loop", "1", "-t", f"{shot_duration:.3f}", "-i", image_path])
        audio_input_index = len(image_paths)
        args.extend(["-i", audio_path])
        args.extend(
            [
                "-filter_complex",
                filter_complex,
                "-map",
                video_output,
                "-map",
                f"{audio_input_index}:a",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-c:a",
                "aac",
                "-shortest",
                str(output_path),
            ],
        )
        self._run(args)

    def _render_single_shot_scene(
        self,
        *,
        image_path: str,
        audio_path: str,
        subtitle_path: str,
        output_path: Path,
        duration_seconds: float,
    ) -> None:
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
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]
        self._run(args)

    def _scale_shot_durations(
        self,
        shot_durations: list[float],
        audio_duration: float,
    ) -> list[float]:
        total = sum(shot_durations)
        if total <= 0:
            even = audio_duration / len(shot_durations)
            return [even for _ in shot_durations]
        scale = audio_duration / total
        return [duration * scale for duration in shot_durations]

    def concat_clips(self, clip_paths: list[Path], output_path: Path) -> None:
        """Concatenate rendered scene clips into the final video."""
        if not clip_paths:
            raise FFmpegError("No scene clips provided for concatenation")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        if len(clip_paths) == 1:
            self._run(["-y", "-i", str(clip_paths[0]), "-c", "copy", str(output_path)])
            return

        if self._settings.scene_transition == "cut":
            self._concat_with_demuxer(clip_paths, output_path)
            return

        durations = [self._probe_duration(path) for path in clip_paths]
        transition_duration = self._transition_duration(durations)
        filter_complex = build_clip_transition_filter(
            clip_count=len(clip_paths),
            durations=durations,
            transition_duration=transition_duration,
        )
        self._concat_with_filter_complex(clip_paths, output_path, filter_complex)

    def _concat_with_filter_complex(
        self,
        clip_paths: list[Path],
        output_path: Path,
        filter_complex: str,
    ) -> None:
        args = ["-y"]
        for path in clip_paths:
            args.extend(["-i", str(path)])
        args.extend(
            [
                "-filter_complex",
                filter_complex,
                "-map",
                "[vout]",
                "-map",
                "[aout]",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-c:a",
                "aac",
                str(output_path),
            ],
        )
        self._run(args)

    def _concat_with_demuxer(self, clip_paths: list[Path], output_path: Path) -> None:
        concat_file = output_path.parent / "concat_list.txt"
        lines = [f"file '{path.resolve().as_posix()}'" for path in clip_paths]
        concat_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self._run(
            [
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
            ],
        )

    def _transition_duration(self, durations: list[float]) -> float:
        requested = self._settings.scene_transition_duration
        shortest = min(durations)
        return min(requested, max(shortest / 2.0 - 0.05, 0.1))

    def _probe_duration(self, clip_path: Path) -> float:
        ffprobe = self._ffprobe_path()
        try:
            result = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "json",
                    str(clip_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise FFmpegError(f"ffprobe not found: {ffprobe}") from exc

        if result.returncode != 0:
            stderr = _format_ffmpeg_stderr(result.stderr or "ffprobe failed")
            raise FFmpegError(stderr)

        payload = json.loads(result.stdout or "{}")
        duration = float(payload.get("format", {}).get("duration", 0.0))
        if duration <= 0:
            raise FFmpegError(f"Could not read duration for {clip_path}")
        return duration

    def _ffprobe_path(self) -> str:
        ffmpeg_path = self._settings.ffmpeg_path
        if ffmpeg_path.endswith("ffmpeg"):
            return f"{ffmpeg_path[:-6]}ffprobe"
        return "ffprobe"

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
            stderr = _format_ffmpeg_stderr(result.stderr or "ffmpeg failed")
            raise FFmpegError(stderr)


def _format_ffmpeg_stderr(stderr: str, *, max_length: int = 500) -> str:
    """Return the most useful part of FFmpeg stderr (errors are usually at the end)."""
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    if not lines:
        return "ffmpeg failed"

    interesting = [
        line
        for line in lines
        if any(
            marker in line
            for marker in (
                "Error",
                "error",
                "Invalid",
                "failed",
                "Failed",
                "No such file",
                "does not match",
                "do not match",
                "Nothing was written",
                "Conversion failed",
            )
        )
    ]
    message = "\n".join(interesting[-5:]) if interesting else "\n".join(lines[-8:])
    if len(message) > max_length:
        return message[-max_length:]
    return message
