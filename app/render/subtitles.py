"""Generate ASS subtitle files with word-level karaoke timing."""

from pathlib import Path

from app.config import Settings, get_settings
from app.models.pipeline import ScriptPlan
from app.models.render import SceneAudio, SceneSubtitle
from app.models.script import ScriptScene


class SubtitleGenerator:
    """Build ASS subtitle files for TikTok-style word highlighting."""

    def __init__(self, *, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def generate(
        self,
        script_plan: ScriptPlan,
        audio_files: list[SceneAudio],
    ) -> list[SceneSubtitle]:
        output_dir = self._subtitles_dir(script_plan)
        output_dir.mkdir(parents=True, exist_ok=True)
        duration_by_scene = {audio.scene_id: audio.duration_seconds for audio in audio_files}

        subtitles: list[SceneSubtitle] = []
        for script_scene in script_plan.script.scenes:
            duration = duration_by_scene.get(script_scene.scene_id, script_scene.duration)
            subtitle_path = output_dir / f"scene_{script_scene.scene:02d}.ass"
            subtitle_path.write_text(
                self.build_ass(script_scene, duration_seconds=duration),
                encoding="utf-8",
            )
            subtitles.append(
                SceneSubtitle(
                    scene_id=script_scene.scene_id,
                    subtitle_path=str(subtitle_path.resolve()),
                ),
            )

        return subtitles

    def build_ass(self, script_scene: ScriptScene, *, duration_seconds: float) -> str:
        """Return ASS content with karaoke-style word timing from the voice text."""
        words = script_scene.voice.split()
        if not words:
            words = [script_scene.overlay]

        timings = self._word_timings(words, duration_seconds)
        header = self._ass_header()
        events = [self._karaoke_event(word, start, end) for word, start, end in timings]
        return header + "\n".join(events) + "\n"

    def _ass_header(self) -> str:
        font_size = self._settings.subtitle_font_size
        width = self._settings.video_width
        height = self._settings.video_height
        return (
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            f"PlayResX: {width}\n"
            f"PlayResY: {height}\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
            "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
            "MarginR, MarginV, Encoding\n"
            f"Style: Default,Arial,{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,"
            "&H64000000,-1,0,0,0,100,100,0,0,1,3,0,2,40,40,120,1\n\n"
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

    def _karaoke_event(self, word: str, start: float, end: float) -> str:
        return (
            f"Dialogue: 0,{self._format_time(start)},{self._format_time(end)},"
            f"Default,,0,0,0,,{{\\kf{int((end - start) * 100)}}}{word.upper()}"
        )

    def _format_time(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        centiseconds = int(round((seconds % 60) * 100))
        return f"{hours}:{minutes:02d}:{centiseconds:02d}.00"

    def _subtitles_dir(self, script_plan: ScriptPlan) -> Path:
        document_id = script_plan.storyboard_result.content_plan.document.id
        return self._settings.output_dir / document_id / "subtitles"
