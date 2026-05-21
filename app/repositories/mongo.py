from typing import Generic, TypeVar

from pydantic import BaseModel

from app.repositories.base import Repository
from app.schemas.common import utc_now

T = TypeVar("T", bound=BaseModel)


class MongoRepository(Repository[T], Generic[T]):
    def __init__(self, collection, model: type[T]) -> None:
        self.collection = collection
        self.model = model

    async def create(self, document: T) -> T:
        await self.collection.insert_one(document.model_dump(mode="json"))
        return document

    async def get(self, document_id: str) -> T | None:
        data = await self.collection.find_one({"id": document_id})
        return self.model(**data) if data else None

    async def list(self) -> list[T]:
        cursor = self.collection.find({})
        return [self.model(**data) async for data in cursor]

    async def update(self, document_id: str, updates: dict) -> T | None:
        updates["updated_at"] = utc_now().isoformat()
        await self.collection.update_one({"id": document_id}, {"$set": updates})
        return await self.get(document_id)

    async def delete_all(self) -> int:
        result = await self.collection.delete_many({})
        return result.deleted_count
