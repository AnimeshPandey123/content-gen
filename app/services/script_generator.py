"""LLM-backed script generation using Gemini."""

from app.agents.gemini_client import GeminiClient, GeminiClientError
from app.config import Settings, get_settings
from app.models.pipeline import StoryboardResult
from app.models.script import Script, ScriptScene, ScriptShot
from app.models.script_generation import GeneratedScriptScene, ScriptGenerationResponse
from app.prompts.script import build_script_prompt


class ScriptGenerationError(Exception):
    """Raised when script generation cannot be completed."""


class ScriptGenerator:
    """Generate voice and overlay text for each storyboard shot."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        gemini_client: GeminiClient | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._gemini_client = gemini_client

    def generate_script(self, storyboard_result: StoryboardResult) -> Script:
        generated_scenes = self._generate_scenes(storyboard_result)
        return self._build_script(storyboard_result, generated_scenes)

    def generate_scenes(self, storyboard_result: StoryboardResult) -> list[GeneratedScriptScene]:
        """Return raw LLM-generated script scenes."""
        return self._generate_scenes(storyboard_result)

    def _generate_scenes(self, storyboard_result: StoryboardResult) -> list[GeneratedScriptScene]:
        prompt = build_script_prompt(storyboard_result, settings=self._settings)
        client = self._gemini_client or self._build_client()

        try:
            response = client.generate_model(prompt, ScriptGenerationResponse)
        except GeminiClientError as exc:
            raise ScriptGenerationError(str(exc)) from exc

        return response.scenes

    def _build_client(self) -> GeminiClient:
        api_key = self._settings.gemini_api_key
        if not api_key:
            raise ScriptGenerationError(
                "GEMINI_API_KEY is not configured for script generation",
            )
        return GeminiClient(api_key=api_key, model=self._settings.gemini_model)

    def _build_script(
        self,
        storyboard_result: StoryboardResult,
        generated_scenes: list[GeneratedScriptScene],
    ) -> Script:
        storyboard_by_number = {
            scene.order + 1: scene for scene in storyboard_result.storyboard.scenes
        }
        script_scenes: list[ScriptScene] = []

        for generated in generated_scenes:
            storyboard_scene = storyboard_by_number.get(generated.scene)
            if storyboard_scene is None:
                continue
            shots = self._build_script_shots(storyboard_scene, generated)
            script_scenes.append(
                ScriptScene(
                    scene=generated.scene,
                    scene_id=storyboard_scene.id,
                    shots=shots,
                ),
            )

        if not script_scenes:
            raise ScriptGenerationError("No script scenes matched the storyboard output")

        return Script(scenes=script_scenes)

    def _build_script_shots(self, storyboard_scene, generated: GeneratedScriptScene) -> list[ScriptShot]:
        expected = len(storyboard_scene.shots)
        generated_by_order = {shot.shot_order: shot for shot in generated.shots}
        if len(generated.shots) != expected:
            raise ScriptGenerationError(
                f"Scene {generated.scene} returned {len(generated.shots)} script shots; "
                f"expected {expected}",
            )

        shots: list[ScriptShot] = []
        for storyboard_shot in storyboard_scene.shots:
            script_shot = generated_by_order.get(storyboard_shot.order)
            if script_shot is None:
                raise ScriptGenerationError(
                    f"Scene {generated.scene} is missing script for shot_order "
                    f"{storyboard_shot.order}",
                )
            shots.append(
                ScriptShot(
                    shot_order=script_shot.shot_order,
                    voice=script_shot.voice,
                    overlay=script_shot.overlay,
                ),
            )
        return shots
