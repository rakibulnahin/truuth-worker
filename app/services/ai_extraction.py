from abc import ABC, abstractmethod

from app.schemas.candidates import NormalizedIdentity
from app.services.resume_parser import ParsedResume


class AIExtractionProvider(ABC):
    @abstractmethod
    async def extract_entities(self, parsed_resume: ParsedResume, hints: dict | None = None) -> NormalizedIdentity:
        raise NotImplementedError


class MockAIExtractionProvider(AIExtractionProvider):
    async def extract_entities(
        self,
        parsed_resume: ParsedResume,
        hints: dict | None = None,
    ) -> NormalizedIdentity:
        hints = hints or {}
        full_name = hints.get("full_name") or "Mock Candidate"
        parts = full_name.split(" ", 1)
        return NormalizedIdentity(
            full_name=full_name,
            first_name=parts[0],
            last_name=parts[1] if len(parts) > 1 else None,
            aliases=hints.get("aliases", []),
            organizations=hints.get("organizations", []),
            locations=hints.get("locations", []),
            keywords=hints.get("keywords", []),
            identifiers={
                "email": hints.get("email"),
                "phone": hints.get("phone"),
                "source_file": parsed_resume.file_name,
                "extraction_provider": "mock",
            },
        )
