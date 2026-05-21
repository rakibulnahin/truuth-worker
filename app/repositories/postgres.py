from typing import Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.repositories.base import Repository
from app.schemas.common import utc_now

T = TypeVar("T", bound=BaseModel)


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url


def create_postgres_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(
        normalize_database_url(database_url),
        pool_pre_ping=True,
        poolclass=NullPool,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
        },
    )


class PostgresDocumentRepository(Repository[T], Generic[T]):
    def __init__(self, engine: AsyncEngine, table_name: str, model: type[T]) -> None:
        self.engine = engine
        self.table_name = table_name
        self.model = model

    async def ensure_table(self) -> None:
        async with self.engine.begin() as connection:
            await connection.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id TEXT PRIMARY KEY,
                        data JSONB NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT now(),
                        updated_at TIMESTAMPTZ DEFAULT now()
                    )
                    """
                )
            )

    async def create(self, document: T) -> T:
        payload = document.model_dump(mode="json")
        async with self.engine.begin() as connection:
            await connection.execute(
                text(
                    f"""
                    INSERT INTO {self.table_name} (id, data, created_at, updated_at)
                    VALUES (:id, CAST(:data AS JSONB), :created_at, :updated_at)
                    ON CONFLICT (id)
                    DO UPDATE SET data = EXCLUDED.data, updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "id": payload["id"],
                    "data": document.model_dump_json(),
                    "created_at": getattr(document, "created_at", None),
                    "updated_at": getattr(document, "updated_at", None),
                },
            )
        return document

    async def get(self, document_id: str) -> T | None:
        async with self.engine.connect() as connection:
            row = (
                await connection.execute(
                    text(f"SELECT data FROM {self.table_name} WHERE id = :id"),
                    {"id": document_id},
                )
            ).first()
        return self.model(**row.data) if row else None

    async def list(self) -> list[T]:
        async with self.engine.connect() as connection:
            rows = (
                await connection.execute(
                    text(f"SELECT data FROM {self.table_name} ORDER BY created_at ASC")
                )
            ).all()
        return [self.model(**row.data) for row in rows]

    async def update(self, document_id: str, updates: dict) -> T | None:
        document = await self.get(document_id)
        if not document:
            return None
        updates["updated_at"] = utc_now()
        updated = document.model_copy(update=updates)
        await self.create(updated)
        return updated

    async def delete_all(self) -> int:
        async with self.engine.begin() as connection:
            result = await connection.execute(text(f"DELETE FROM {self.table_name}"))
        return result.rowcount or 0
