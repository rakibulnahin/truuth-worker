from __future__ import annotations

from collections.abc import Callable
from typing import Generic, TypeVar

from pydantic import BaseModel

from app.schemas.common import utc_now

T = TypeVar("T", bound=BaseModel)


class Repository(Generic[T]):
    async def create(self, document: T) -> T:
        raise NotImplementedError

    async def get(self, document_id: str) -> T | None:
        raise NotImplementedError

    async def list(self) -> list[T]:
        raise NotImplementedError

    async def update(self, document_id: str, updates: dict) -> T | None:
        raise NotImplementedError

    async def delete_all(self) -> int:
        raise NotImplementedError

    async def find(self, predicate: Callable[[T], bool]) -> list[T]:
        documents = await self.list()
        return [document for document in documents if predicate(document)]


class InMemoryRepository(Repository[T]):
    def __init__(self) -> None:
        self._documents: dict[str, T] = {}

    async def create(self, document: T) -> T:
        self._documents[getattr(document, "id")] = document
        return document

    async def get(self, document_id: str) -> T | None:
        return self._documents.get(document_id)

    async def list(self) -> list[T]:
        return list(self._documents.values())

    async def update(self, document_id: str, updates: dict) -> T | None:
        document = self._documents.get(document_id)
        if not document:
            return None
        updates["updated_at"] = utc_now()
        updated = document.model_copy(update=updates)
        self._documents[document_id] = updated
        return updated

    async def delete_all(self) -> int:
        deleted_count = len(self._documents)
        self._documents.clear()
        return deleted_count
