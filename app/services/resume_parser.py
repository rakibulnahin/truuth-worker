from abc import ABC, abstractmethod

from pydantic import BaseModel


class ParsedResume(BaseModel):
    file_name: str
    text: str
    metadata: dict = {}


class ResumeParser(ABC):
    @abstractmethod
    async def parse(self, file_name: str, file_bytes: bytes | None = None) -> ParsedResume:
        raise NotImplementedError


class MockResumeParser(ResumeParser):
    async def parse(self, file_name: str, file_bytes: bytes | None = None) -> ParsedResume:
        return ParsedResume(
            file_name=file_name,
            text=f"Mock parsed resume text for {file_name}",
            metadata={
                "parser": "mock",
                "ocr_performed": False,
                "resume_retained": False,
                "byte_count": len(file_bytes or b""),
            },
        )
