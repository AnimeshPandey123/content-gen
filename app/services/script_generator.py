"""LLM-backed script generation using Gemini."""

from app.agents.gemini_client import GeminiClient, GeminiClientError
from app.config import Settings, get_settings
from app.models.pipeline import StoryboardResult
from app.models.script import Script, ScriptScene
from app.models.script_generation import GeneratedScriptScene, ScriptGenerationResponse
from app.prompts.script import build_script_prompt


class ScriptGenerationError(Exception):
    """Raised when script generation cannot be completed."""


class ScriptGenerator:
    """Generate voice and overlay text for each storyboard scene."""

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
        scene_ids = {scene.order + 1: scene.id for scene in storyboard_result.storyboard.scenes}
        storyboard_scenes = {
            scene.order + 1: scene for scene in storyboard_result.storyboard.scenes
        }
        script_scenes: list[ScriptScene] = []

        for generated in generated_scenes:
            scene_id = scene_ids.get(generated.scene)
            storyboard_scene = storyboard_scenes.get(generated.scene)
            if scene_id is None or storyboard_scene is None:
                continue
            script_scenes.append(
                ScriptScene(
                    scene=generated.scene,
                    scene_id=scene_id,
                    voice=generated.voice,
                    overlay=generated.overlay,
                    duration=storyboard_scene.duration_seconds,
                ),
            )

        if not script_scenes:
            raise ScriptGenerationError("No script scenes matched the storyboard output")

        return Script(scenes=script_scenes)
