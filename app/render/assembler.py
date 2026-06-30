"""Assemble scene clips and the final video from rendered assets."""

from pathlib import Path

from app.config import Settings, get_settings
from app.models.render import RenderProject, SceneClip
from app.render.audio import probe_wav_duration
from app.render.ffmpeg import FFmpegRenderer
from app.render.project import clip_path, final_video_path
from app.services.timeline_builder import TimelineBuilder


class VideoAssembler:
    """Feature 12: combine screenshot, audio, and subtitle assets into video files."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        ffmpeg_renderer: FFmpegRenderer | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._ffmpeg_renderer = ffmpeg_renderer or FFmpegRenderer(settings=self._settings)
        self._timeline_builder = TimelineBuilder()

    def render(self, project: RenderProject) -> RenderProject:
        """Render each scene clip and concatenate them into the final MP4."""
        project_dir = Path(project.project_dir)
        clips_dir = project_dir / "clips"
        clips_dir.mkdir(parents=True, exist_ok=True)
        storyboard_scenes = {
            scene.id: scene for scene in project.script_plan.storyboard_result.storyboard.scenes
        }

        scene_clips: list[SceneClip] = []
        for scene in project.scenes:
            if not scene.audio_path or not scene.subtitle_path:
                raise ValueError(f"Scene {scene.scene_id} is missing required assets")

            image_paths = scene.shot_screenshot_paths or (
                [scene.screenshot_path] if scene.screenshot_path else []
            )
            if not image_paths:
                raise ValueError(f"Scene {scene.scene_id} is missing screenshot assets")

            storyboard_scene = storyboard_scenes[scene.scene_id]
            shot_durations = self._timeline_builder.shot_durations(storyboard_scene)
            if len(shot_durations) != len(image_paths):
                even_duration = storyboard_scene.duration_seconds / len(image_paths)
                shot_durations = [even_duration for _ in image_paths]

            output_path = clip_path(project_dir, scene.scene_number)
            audio_duration = scene.audio_duration_seconds
            if audio_duration is None:
                audio_duration = probe_wav_duration(Path(scene.audio_path))
            self._ffmpeg_renderer.render_scene(
                image_paths=image_paths,
                shot_durations=shot_durations,
                audio_path=scene.audio_path,
                subtitle_path=scene.subtitle_path,
                output_path=output_path,
                duration_seconds=audio_duration,
            )
            scene_clips.append(
                SceneClip(scene_id=scene.scene_id, clip_path=str(output_path.resolve())),
            )

        video_path = final_video_path(
            project_dir,
            project.script_plan.storyboard_result.content_plan.document.id,
        )
        self._ffmpeg_renderer.concat_clips(
            [Path(item.clip_path) for item in scene_clips],
            video_path,
        )

        return project.with_clips(scene_clips).with_video_path(str(video_path.resolve()))
