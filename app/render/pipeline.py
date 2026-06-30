"""Orchestrate deterministic media production for the MVP renderer."""

from pathlib import Path

from app.config import Settings, get_settings
from app.models.pipeline import ScriptPlan
from app.models.render import RenderArtifacts, SceneClip
from app.render.ffmpeg import FFmpegRenderer
from app.render.screenshot import ScreenshotGenerator
from app.render.subtitles import SubtitleGenerator
from app.render.voice import VoiceGenerator


class RenderPipeline:
    """Execute screenshot, voice, subtitle, and FFmpeg rendering stages."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        screenshot_generator: ScreenshotGenerator | None = None,
        voice_generator: VoiceGenerator | None = None,
        subtitle_generator: SubtitleGenerator | None = None,
        ffmpeg_renderer: FFmpegRenderer | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._screenshot_generator = screenshot_generator or ScreenshotGenerator(
            settings=self._settings,
        )
        self._voice_generator = voice_generator or VoiceGenerator(settings=self._settings)
        self._subtitle_generator = subtitle_generator or SubtitleGenerator(
            settings=self._settings,
        )
        self._ffmpeg_renderer = ffmpeg_renderer or FFmpegRenderer(settings=self._settings)

    def run(self, script_plan: ScriptPlan) -> RenderArtifacts:
        document_id = script_plan.storyboard_result.content_plan.document.id
        project_dir = self._settings.output_dir / document_id
        project_dir.mkdir(parents=True, exist_ok=True)

        screenshots = self._screenshot_generator.generate(script_plan)
        audio_files = self._voice_generator.generate(script_plan)
        subtitle_files = self._subtitle_generator.generate(script_plan, audio_files)
        scene_clips = self._render_scene_clips(
            script_plan,
            screenshots=screenshots,
            audio_files=audio_files,
            subtitle_files=subtitle_files,
            clips_dir=project_dir / "clips",
        )

        video_path = project_dir / f"{document_id}.mp4"
        self._ffmpeg_renderer.concat_clips(
            [Path(clip.clip_path) for clip in scene_clips],
            video_path,
        )

        return RenderArtifacts(
            project_dir=str(project_dir),
            screenshots=screenshots,
            audio_files=audio_files,
            subtitle_files=subtitle_files,
            scene_clips=scene_clips,
            video_path=str(video_path.resolve()),
        )

    def _render_scene_clips(
        self,
        script_plan: ScriptPlan,
        *,
        screenshots,
        audio_files,
        subtitle_files,
        clips_dir: Path,
    ) -> list[SceneClip]:
        clips_dir.mkdir(parents=True, exist_ok=True)
        screenshot_by_scene = {item.scene_id: item for item in screenshots}
        audio_by_scene = {item.scene_id: item for item in audio_files}
        subtitle_by_scene = {item.scene_id: item for item in subtitle_files}
        scene_clips: list[SceneClip] = []

        for script_scene in script_plan.script.scenes:
            clip_path = clips_dir / f"scene_{script_scene.scene:02d}.mp4"
            audio = audio_by_scene[script_scene.scene_id]
            screenshot = screenshot_by_scene[script_scene.scene_id]
            subtitle = subtitle_by_scene[script_scene.scene_id]
            self._ffmpeg_renderer.render_scene(
                image_path=screenshot.image_path,
                audio_path=audio.audio_path,
                subtitle_path=subtitle.subtitle_path,
                output_path=clip_path,
                duration_seconds=audio.duration_seconds,
            )
            scene_clips.append(SceneClip(scene_id=script_scene.scene_id, clip_path=str(clip_path)))

        return scene_clips
