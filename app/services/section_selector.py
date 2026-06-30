"""LLM-backed section selection using Gemini."""

import re

from app.agents.gemini_client import GeminiClient, GeminiClientError
from app.config import Settings, get_settings
from app.models.document import Document
from app.models.section import Section
from app.models.section_selection import RankedSection, SectionSelectionResponse
from app.prompts.section_selection import build_section_selection_prompt
from app.services.document_sections import SectionCandidate, extract_section_candidates


class SectionSelectionError(Exception):
    """Raised when section selection cannot be completed."""


class SectionSelector:
    """Select the most interesting document sections with Gemini."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        gemini_client: GeminiClient | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._gemini_client = gemini_client

    def select_sections(self, document: Document) -> list[Section]:
        candidates = extract_section_candidates(document)
        rankings = self._rank_sections(document, candidates)
        return self._build_sections(document, candidates, rankings)

    def rank_sections(self, document: Document) -> list[RankedSection]:
        """Return raw LLM rankings for the document."""
        candidates = extract_section_candidates(document)
        return self._rank_sections(document, candidates)

    def _rank_sections(
        self,
        document: Document,
        candidates: list[SectionCandidate],
    ) -> list[RankedSection]:
        limit = min(self._settings.section_selection_limit, len(candidates))
        prompt = build_section_selection_prompt(
            candidates,
            limit=limit,
            document_title=document.title,
        )
        client = self._gemini_client or self._build_client()

        try:
            response = client.generate_model(prompt, SectionSelectionResponse)
        except GeminiClientError as exc:
            raise SectionSelectionError(str(exc)) from exc

        return response.sections[:limit]

    def _build_client(self) -> GeminiClient:
        api_key = self._settings.gemini_api_key
        if not api_key:
            raise SectionSelectionError(
                "GEMINI_API_KEY is not configured for section selection",
            )
        return GeminiClient(api_key=api_key, model=self._settings.gemini_model)

    def _build_sections(
        self,
        document: Document,
        candidates: list[SectionCandidate],
        rankings: list[RankedSection],
    ) -> list[Section]:
        sections: list[Section] = []
        for index, ranked in enumerate(rankings, start=1):
            candidate = _match_candidate(candidates, ranked.section)
            if candidate is None:
                continue
            sections.append(
                Section(
                    id=f"{document.id}-section-{index}",
                    title=candidate.title,
                    content=candidate.content,
                    page_numbers=candidate.page_numbers or [document.pages[0].page_number],
                    paragraph_indices=candidate.paragraph_indices,
                    importance_score=ranked.importance,
                ),
            )

        if not sections:
            raise SectionSelectionError("No sections matched the LLM selection output")

        return sections


def _match_candidate(
    candidates: list[SectionCandidate],
    section_title: str,
) -> SectionCandidate | None:
    normalized_target = _normalize_title(section_title)
    for candidate in candidates:
        if _normalize_title(candidate.title) == normalized_target:
            return candidate

    for candidate in candidates:
        normalized_candidate = _normalize_title(candidate.title)
        if normalized_target in normalized_candidate or normalized_candidate in normalized_target:
            return candidate

    return None


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().casefold())
