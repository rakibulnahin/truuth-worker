from abc import ABC, abstractmethod

from app.schemas.payloads import PayloadEntryDocument
from app.schemas.screening import NormalizedScreeningResult


class VendorAdapter(ABC):
    vendor_name: str

    @abstractmethod
    async def submit_payload(self, entries: list[PayloadEntryDocument]) -> str:
        raise NotImplementedError

    @abstractmethod
    async def poll_results(self, execution_id: str, entries: list[PayloadEntryDocument]) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def normalize_results(
        self,
        run_id: str,
        raw_response: dict,
        entries: list[PayloadEntryDocument],
    ) -> list[NormalizedScreeningResult]:
        raise NotImplementedError
