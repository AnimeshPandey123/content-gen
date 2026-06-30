"""Gemini API client for structured JSON responses."""

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class GeminiClientError(Exception):
    """Raised when the Gemini API call fails."""


class GeminiClient:
    """Thin wrapper around the Google Gemini API."""

    def __init__(self, *, api_key: str, model: str) -> None:
        if not api_key:
            raise GeminiClientError("Gemini API key is required")

        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate_model(self, prompt: str, response_model: type[T]) -> T:
        """Generate structured output and validate it against a Pydantic model."""
        from google.genai import types

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
        except Exception as exc:
            raise GeminiClientError(f"Gemini request failed: {exc}") from exc

        text = response.text
        if not text:
            raise GeminiClientError("Gemini returned an empty response")

        try:
            return response_model.model_validate_json(text)
        except ValidationError as exc:
            raise GeminiClientError(f"Gemini returned invalid JSON: {exc}") from exc

    def generate_json(self, prompt: str) -> object:
        """Generate and parse arbitrary JSON output."""
        from google.genai import types

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
        except Exception as exc:
            raise GeminiClientError(f"Gemini request failed: {exc}") from exc

        if not response.text:
            raise GeminiClientError("Gemini returned an empty response")

        try:
            return json.loads(response.text)
        except json.JSONDecodeError as exc:
            raise GeminiClientError(f"Gemini returned invalid JSON: {exc}") from exc
