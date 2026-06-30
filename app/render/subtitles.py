"""Generate ASS subtitle assets with word-level karaoke timing."""

from pathlib import Path

from app.config import Settings, get_settings
from app.models.render import RenderProject, SceneAudio, SceneSubtitle
from app.models.script import ScriptScene
from app.render.project import subtitle_path

_WORDS_PER_LINE = 5


class SubtitleGenerator:
    """Feature 10: build ASS subtitle assets aligned to narration audio."""

    def __init__(self, *, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def produce(
        self,
        project: RenderProject,
        audio_files: list[SceneAudio],
    ) -> list[SceneSubtitle]:
        project_dir = Path(project.project_dir)
        subtitles_dir = project_dir / "subtitles"
        subtitles_dir.mkdir(parents=True, exist_ok=True)
        duration_by_scene = {audio.scene_id: audio.duration_seconds for audio in audio_files}

        subtitles: list[SceneSubtitle] = []
        for script_scene in project.script_plan.script.scenes:
            duration = duration_by_scene.get(script_scene.scene_id, script_scene.duration)
            output_path = subtitle_path(project_dir, script_scene.scene)
            output_path.write_text(
                self.build_ass(script_scene, duration_seconds=duration),
                encoding="utf-8",
            )
            subtitles.append(
                SceneSubtitle(
                    scene_id=script_scene.scene_id,
                    subtitle_path=str(output_path.resolve()),
                ),
            )

        return subtitles

    def build_ass(self, script_scene: ScriptScene, *, duration_seconds: float) -> str:
        """Return ASS content with readable karaoke captions for the scene."""
        text = script_scene.voice.strip() or script_scene.overlay.strip()
        words = text.split()
        if not words:
            words = [script_scene.overlay.strip() or " "]

        timings = self._word_timings(words, duration_seconds)
        caption_text = self._build_caption_text(timings)
        header = self._ass_header()
        event = (
            f"Dialogue: 0,{self._format_time(0.0)},{self._format_time(duration_seconds)},"
            f"Default,,0,0,0,,{caption_text}"
        )
        return header + event + "\n"

    def _ass_header(self) -> str:
        font_size = self._settings.subtitle_font_size
        width = self._settings.video_width
        height = self._settings.video_height
        margin_v = max(int(height * 0.12), 120)
        return (
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            f"PlayResX: {width}\n"
            f"PlayResY: {height}\n"
            "WrapStyle: 0\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
            "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
            "MarginR, MarginV, Encoding\n"
            f"Style: Default,Arial,{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,"
            f"&HC0000000,-1,0,0,0,100,100,0,0,1,4,1,2,60,60,{margin_v},1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
            "Effect, Text\n"
        )

    def _word_timings(
        self,
        words: list[str],
        duration_seconds: float,
    ) -> list[tuple[str, float, float]]:
        weights = [max(len(word), 1) for word in words]
        total_weight = sum(weights)
        elapsed = 0.0
        timings: list[tuple[str, float, float]] = []

        for word, weight in zip(words, weights, strict=True):
            word_duration = duration_seconds * (weight / total_weight)
            start = elapsed
            end = elapsed + word_duration
            timings.append((word, start, end))
            elapsed = end

        return timings

    def _build_caption_text(self, timings: list[tuple[str, float, float]]) -> str:
        lines: list[str] = []
        for index in range(0, len(timings), _WORDS_PER_LINE):
            chunk = timings[index : index + _WORDS_PER_LINE]
            line = " ".join(
                self._format_karaoke_word(word, start, end) for word, start, end in chunk
            )
            lines.append(line)
        return r"\N".join(lines)

    def _format_karaoke_word(self, word: str, start: float, end: float) -> str:
        duration_cs = max(int(round((end - start) * 100)), 1)
        return f"{{\\kf{duration_cs}}}{word}"

    def _format_time(self, seconds: float) -> str:
        total_centiseconds = int(round(max(seconds, 0.0) * 100))
        hours = total_centiseconds // 360_000
        minutes = (total_centiseconds % 360_000) // 6_000
        secs = (total_centiseconds % 6_000) // 100
        centiseconds = total_centiseconds % 100
        return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"
