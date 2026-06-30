"""Caption / subtitle model."""

from pydantic import BaseModel, Field, model_validator


class Caption(BaseModel):
    """Timed on-screen caption for a scene."""

    scene_id: str
    text: str = Field(min_length=1)
    start_time: float = Field(ge=0)
    end_time: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_timing(self) -> "Caption":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be greater than start_time")
        return self
