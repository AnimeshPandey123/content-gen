"""Assemble scene clips and the final video from rendered assets."""

from pathlib import Path

from app.config import Settings, get_settings
from app.models.render import RenderProject, SceneClip
from app.render.ffmpeg import FFmpegRenderer
from app.render.project import clip_path, final_video_path


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

    def render(self, project: RenderProject) -> RenderProject:
        """Render each scene clip and concatenate them into the final MP4."""
        project_dir = Path(project.project_dir)
        clips_dir = project_dir / "clips"
        clips_dir.mkdir(parents=True, exist_ok=True)

        scene_clips: list[SceneClip] = []
        for scene in project.scenes:
            if not scene.screenshot_path or not scene.audio_path or not scene.subtitle_path:
                raise ValueError(f"Scene {scene.scene_id} is missing required assets")

            output_path = clip_path(project_dir, scene.scene_number)
            self._ffmpeg_renderer.render_scene(
                image_path=scene.screenshot_path,
                audio_path=scene.audio_path,
                subtitle_path=scene.subtitle_path,
                output_path=output_path,
                duration_seconds=scene.audio_duration_seconds
                or project.script_plan.script.scenes[scene.scene_number - 1].duration,
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
