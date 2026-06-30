"""Build absolute timelines from storyboard scenes and shots."""

from app.models.scene import Scene, SceneShot
from app.models.timeline import SceneTimeline, TimelineSegment, VideoTimeline
from app.services.duration_budget import playback_duration


class TimelineBuilder:
    """Convert relative shot durations into absolute time-based timelines."""

    def build_scene_timeline(self, scene: Scene) -> SceneTimeline:
        """Build a 0-based scene timeline from ordered shots."""
        segments: list[TimelineSegment] = []
        cursor = 0.0
        for shot in sorted(scene.shots, key=lambda item: item.order):
            end_seconds = cursor + shot.duration_seconds
            segments.append(
                TimelineSegment(
                    start_seconds=round(cursor, 3),
                    end_seconds=round(end_seconds, 3),
                    kind="shot",
                    goal=shot.goal,
                    shot_order=shot.order,
                ),
            )
            cursor = end_seconds
        return SceneTimeline(duration_seconds=round(scene.duration_seconds, 3), segments=segments)

    def scale_scene_timeline(
        self,
        timeline: SceneTimeline,
        new_duration_seconds: float,
    ) -> SceneTimeline:
        """Scale all segment boundaries to a new scene duration."""
        if timeline.duration_seconds <= 0:
            return timeline.model_copy(update={"duration_seconds": round(new_duration_seconds, 3)})

        scale = new_duration_seconds / timeline.duration_seconds
        segments = [
            segment.model_copy(
                update={
                    "start_seconds": round(segment.start_seconds * scale, 3),
                    "end_seconds": round(segment.end_seconds * scale, 3),
                },
            )
            for segment in timeline.segments
            if segment.kind == "shot"
        ]
        return SceneTimeline(
            duration_seconds=round(new_duration_seconds, 3),
            segments=segments,
        )

    def apply_scene_timeline(self, scene: Scene, timeline: SceneTimeline) -> Scene:
        """Sync shot timing fields and attach the scene timeline."""
        shots_by_order = {shot.order: shot for shot in scene.shots}
        updated_shots: list[SceneShot] = []
        for segment in timeline.segments:
            if segment.kind != "shot" or segment.shot_order is None:
                continue
            shot = shots_by_order[segment.shot_order]
            duration = segment.end_seconds - segment.start_seconds
            updated_shots.append(
                shot.model_copy(
                    update={
                        "start_seconds": segment.start_seconds,
                        "end_seconds": segment.end_seconds,
                        "duration_seconds": round(duration, 3),
                    },
                ),
            )
        return scene.model_copy(
            update={
                "duration_seconds": timeline.duration_seconds,
                "shots": updated_shots,
                "timeline": timeline,
            },
        )

    def finalize_scene(self, scene: Scene) -> Scene:
        """Ensure a scene has an absolute timeline aligned to its duration."""
        timeline = scene.timeline or self.build_scene_timeline(scene)
        if abs(timeline.duration_seconds - scene.duration_seconds) > 0.001:
            timeline = self.scale_scene_timeline(timeline, scene.duration_seconds)
        return self.apply_scene_timeline(scene, timeline)

    def build_video_timeline(
        self,
        scenes: list[Scene],
        *,
        transition_duration_seconds: float,
    ) -> VideoTimeline:
        """Build a global timeline with shot segments and transition markers."""
        ordered_scenes = sorted(scenes, key=lambda scene: scene.order)
        segments: list[TimelineSegment] = []
        cursor = 0.0

        for index, scene in enumerate(ordered_scenes):
            scene_timeline = scene.timeline or self.build_scene_timeline(scene)
            for segment in scene_timeline.segments:
                if segment.kind != "shot":
                    continue
                segments.append(
                    TimelineSegment(
                        start_seconds=round(cursor + segment.start_seconds, 3),
                        end_seconds=round(cursor + segment.end_seconds, 3),
                        kind="shot",
                        goal=segment.goal,
                        shot_order=segment.shot_order,
                        scene_id=scene.id,
                    ),
                )
            cursor += scene.duration_seconds
            if index < len(ordered_scenes) - 1 and transition_duration_seconds > 0:
                segments.append(
                    TimelineSegment(
                        start_seconds=round(cursor, 3),
                        end_seconds=round(cursor + transition_duration_seconds, 3),
                        kind="transition",
                        goal="Transition",
                        scene_id=scene.id,
                    ),
                )
                cursor += transition_duration_seconds

        scene_durations = [scene.duration_seconds for scene in ordered_scenes]
        playback_seconds = playback_duration(
            scene_durations,
            transition_duration_seconds=transition_duration_seconds,
        )
        if transition_duration_seconds <= 0:
            playback_seconds = sum(scene_durations)

        return VideoTimeline(
            duration_seconds=round(playback_seconds, 3),
            segments=segments,
        )

    def shot_durations(self, scene: Scene) -> list[float]:
        """Return per-shot durations from the scene timeline when available."""
        if scene.timeline:
            return [
                segment.duration_seconds
                for segment in scene.timeline.segments
                if segment.kind == "shot"
            ]
        return [shot.duration_seconds for shot in sorted(scene.shots, key=lambda item: item.order)]
