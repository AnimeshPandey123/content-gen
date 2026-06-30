"""Script generation stage."""

from app.config import Settings, get_settings
from app.models.pipeline import ScriptPlan, StoryboardResult
from app.services.script_generator import ScriptGenerator
from app.workflows.stage import Stage


class ScriptGenerationStage(Stage[StoryboardResult, ScriptPlan]):
    """Generate voice and overlay text for each storyboard scene."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        generator: ScriptGenerator | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._generator = generator or ScriptGenerator(settings=self._settings)

    @property
    def name(self) -> str:
        return "script_generation"

    def run(self, input_model: StoryboardResult) -> ScriptPlan:
        script = self._generator.generate_script(input_model)
        return ScriptPlan(storyboard_result=input_model, script=script)
