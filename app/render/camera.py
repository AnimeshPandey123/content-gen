"""Camera motion filter builders for FFmpeg."""

from typing import Literal

CameraMotion = Literal["static", "zoom", "pan", "ken_burns", "highlight"]


def _scale_to_frame_filter(width: int, height: int) -> str:
    """Fit the screenshot inside the frame without center-cropping away context."""
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black"
    )


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
    base = _scale_to_frame_filter(width, height)
    motion_filter = _motion_filter(motion, width=width, height=height, fps=fps, frames=frames)
    filters = [base, motion_filter]
    if ass_path:
        escaped = ass_path.replace("\\", "/").replace(":", r"\:")
        filters.append(f"ass={escaped}")
    return ",".join(filters)


def build_multi_shot_video_filter(
    *,
    shot_count: int,
    motion: str,
    width: int,
    height: int,
    fps: int,
    ass_path: str | None = None,
) -> tuple[str, str]:
    """Build a filter graph that concatenates multiple still shots into one scene."""
    if shot_count < 1:
        raise ValueError("At least one shot is required")

    filters: list[str] = []
    labels: list[str] = []
    for index in range(shot_count):
        base = _scale_to_frame_filter(width, height)
        motion_filter = _motion_filter(
            motion,
            width=width,
            height=height,
            fps=fps,
            frames=max(fps, 1),
        )
        label = f"v{index}"
        filters.append(f"[{index}:v]{base},{motion_filter},setsar=1[{label}]")
        labels.append(f"[{label}]")

    filters.append(f"{''.join(labels)}concat=n={shot_count}:v=1:a=0[vcat]")
    if ass_path:
        escaped = ass_path.replace("\\", "/").replace(":", r"\:")
        filters.append(f"[vcat]ass={escaped}[vout]")
        return ";".join(filters), "[vout]"
    return ";".join(filters), "[vcat]"


def build_clip_concat_filter(*, clip_count: int) -> str:
    """Build a filter_complex graph that hard-cuts scene clips on narration boundaries."""
    if clip_count < 2:
        raise ValueError("At least two clips are required for concatenation")

    video_inputs = "".join(f"[{index}:v]" for index in range(clip_count))
    audio_inputs = "".join(f"[{index}:a]" for index in range(clip_count))
    return (
        f"{video_inputs}concat=n={clip_count}:v=1:a=0[vout];"
        f"{audio_inputs}concat=n={clip_count}:v=0:a=1[aout]"
    )


def build_clip_transition_filter(
    *,
    clip_count: int,
    durations: list[float],
    transition_duration: float,
) -> str:
    """Build an FFmpeg filter_complex graph that crossfades scene clips."""
    if clip_count < 2:
        raise ValueError("At least two clips are required for transitions")

    video_filters: list[str] = []
    audio_filters: list[str] = []
    current_video = "[0:v]"
    current_audio = "[0:a]"

    for index in range(1, clip_count):
        offset = sum(durations[:index]) - index * transition_duration
        video_label = "[vout]" if index == clip_count - 1 else f"[v{index}]"
        audio_label = "[aout]" if index == clip_count - 1 else f"[a{index}]"
        video_filters.append(
            f"{current_video}[{index}:v]xfade=transition=fade:duration={transition_duration:.3f}"
            f":offset={offset:.3f}{video_label}",
        )
        audio_filters.append(
            f"{current_audio}[{index}:a]acrossfade=d={transition_duration:.3f}{audio_label}",
        )
        current_video = video_label
        current_audio = audio_label

    return ";".join(video_filters + audio_filters)


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
    return f"fps={fps}"
