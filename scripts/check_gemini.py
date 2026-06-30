#!/usr/bin/env python3
"""Verify Gemini API key and model from .env."""

import sys

from app.agents.gemini_client import GeminiClient, GeminiClientError
from app.config import get_settings


def main() -> int:
    settings = get_settings()
    if not settings.gemini_api_key:
        print("ERROR: GEMINI_API_KEY is not set (see .env.example)")
        return 1

    try:
        client = GeminiClient(api_key=settings.gemini_api_key, model=settings.gemini_model)
        result = client.generate_json('Reply with JSON only: {"ok": true}')
    except GeminiClientError as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"OK: Gemini is reachable (model={settings.gemini_model})")
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
