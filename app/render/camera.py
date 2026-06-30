"""Camera motion filter builders for FFmpeg."""

from typing import Literal

CameraMotion = Literal["static", "zoom", "pan", "ken_burns", "highlight"]


def build_video_filter(
    *,
    motion: str,
    width: int,
    height: int,
    fps: int,
    duration_seconds: float,
    ass_path: str | None = None,
) -> str:
    """Build an FFmpeg -vf filter chain for camera motion and subtitles."""
    frames = max(int(duration_seconds * fps), 1)
    base = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
    )
    motion_filter = _motion_filter(motion, width=width, height=height, fps=fps, frames=frames)
    filters = [base, motion_filter]
    if ass_path:
        escaped = ass_path.replace("\\", "/").replace(":", r"\:")
        filters.append(f"ass={escaped}")
    return ",".join(filters)


def _motion_filter(
    motion: str,
    *,
    width: int,
    height: int,
    fps: int,
    frames: int,
) -> str:
    size = f"{width}x{height}"
    if motion == "static":
        return f"fps={fps}"
    if motion == "zoom":
        return (
            f"zoompan=z='min(zoom+0.002,1.35)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={size}:fps={fps}"
        )
    if motion == "pan":
        return (
            f"zoompan=z='1.2':x='if(lte(on,1),(iw-iw/zoom)/2,x+2)':y='(ih-ih/zoom)/2'"
            f":d={frames}:s={size}:fps={fps}"
        )
    if motion == "highlight":
        return (
            f"zoompan=z='1.1':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={size}:fps={fps},"
            f"drawbox=x={width // 4}:y={height // 3}:w={width // 2}:h={height // 4}:"
            f"color=yellow@0.35:t=fill"
        )
    return (
        f"zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s={size}:fps={fps}"
    )
