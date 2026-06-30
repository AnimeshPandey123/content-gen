"""Unit tests for Gemini client error handling."""

import pytest
from app.agents.gemini_client import GeminiClient, GeminiClientError
from app.models.section_selection import SectionSelectionResponse


def test_gemini_client_requires_api_key() -> None:
    with pytest.raises(GeminiClientError, match="API key"):
        GeminiClient(api_key="", model="gemini-2.0-flash")


def test_generate_model_validates_response(monkeypatch) -> None:
    class _Response:
        text = '{"sections": [{"section": "Results", "importance": 0.95}]}'

    class _Models:
        def generate_content(self, **_kwargs):
            return _Response()

    class _Client:
        models = _Models()

    monkeypatch.setattr(
        "google.genai.Client",
        lambda api_key: _Client(),
    )

    client = GeminiClient(api_key="test-key", model="gemini-2.0-flash")
    result = client.generate_model("prompt", SectionSelectionResponse)

    assert result.sections[0].section == "Results"


def test_generate_model_raises_on_invalid_json(monkeypatch) -> None:
    class _Response:
        text = '{"sections": [{"section": "", "importance": 2.0}]}'

    class _Models:
        def generate_content(self, **_kwargs):
            return _Response()

    class _Client:
        models = _Models()

    monkeypatch.setattr(
        "google.genai.Client",
        lambda api_key: _Client(),
    )

    client = GeminiClient(api_key="test-key", model="gemini-2.0-flash")

    with pytest.raises(GeminiClientError, match="invalid JSON"):
        client.generate_model("prompt", SectionSelectionResponse)


def test_generate_model_raises_on_empty_response(monkeypatch) -> None:
    class _Response:
        text = ""

    class _Models:
        def generate_content(self, **_kwargs):
            return _Response()

    class _Client:
        models = _Models()

    monkeypatch.setattr(
        "google.genai.Client",
        lambda api_key: _Client(),
    )

    client = GeminiClient(api_key="test-key", model="gemini-2.0-flash")

    with pytest.raises(GeminiClientError, match="empty response"):
        client.generate_model("prompt", SectionSelectionResponse)


def test_generate_model_raises_on_api_failure(monkeypatch) -> None:
    class _Models:
        def generate_content(self, **_kwargs):
            raise RuntimeError("network down")

    class _Client:
        models = _Models()

    monkeypatch.setattr(
        "google.genai.Client",
        lambda api_key: _Client(),
    )

    client = GeminiClient(api_key="test-key", model="gemini-2.0-flash")

    with pytest.raises(GeminiClientError, match="request failed"):
        client.generate_model("prompt", SectionSelectionResponse)


def test_generate_json_parses_response(monkeypatch) -> None:
    class _Response:
        text = '{"ok": true}'

    class _Models:
        def generate_content(self, **_kwargs):
            return _Response()

    class _Client:
        models = _Models()

    monkeypatch.setattr(
        "google.genai.Client",
        lambda api_key: _Client(),
    )

    client = GeminiClient(api_key="test-key", model="gemini-2.0-flash")
    assert client.generate_json("prompt") == {"ok": True}


def test_generate_json_raises_on_empty_response(monkeypatch) -> None:
    class _Response:
        text = ""

    class _Models:
        def generate_content(self, **_kwargs):
            return _Response()

    class _Client:
        models = _Models()

    monkeypatch.setattr(
        "google.genai.Client",
        lambda api_key: _Client(),
    )

    client = GeminiClient(api_key="test-key", model="gemini-2.0-flash")

    with pytest.raises(GeminiClientError, match="empty response"):
        client.generate_json("prompt")


def test_generate_json_raises_on_api_failure(monkeypatch) -> None:
    class _Models:
        def generate_content(self, **_kwargs):
            raise RuntimeError("network down")

    class _Client:
        models = _Models()

    monkeypatch.setattr(
        "google.genai.Client",
        lambda api_key: _Client(),
    )

    client = GeminiClient(api_key="test-key", model="gemini-2.0-flash")

    with pytest.raises(GeminiClientError, match="request failed"):
        client.generate_json("prompt")


def test_generate_json_raises_on_invalid_json(monkeypatch) -> None:
    class _Response:
        text = "not-json"

    class _Models:
        def generate_content(self, **_kwargs):
            return _Response()

    class _Client:
        models = _Models()

    monkeypatch.setattr(
        "google.genai.Client",
        lambda api_key: _Client(),
    )

    client = GeminiClient(api_key="test-key", model="gemini-2.0-flash")

    with pytest.raises(GeminiClientError, match="invalid JSON"):
        client.generate_json("prompt")
