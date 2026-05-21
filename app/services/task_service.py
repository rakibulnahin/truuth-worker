from datetime import timedelta

from app.repositories.store import RepositoryStore
from app.schemas.common import ExecutionState, utc_now
from app.schemas.tasks import TaskRunDocument


class TaskService:
    def __init__(self, store: RepositoryStore) -> None:
        self.store = store

    async def enqueue(
        self,
        task_type: str,
        payload_snapshot: dict,
        execution_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> TaskRunDocument:
        if idempotency_key:
            existing = await self.store.task_runs.find(
                lambda task: task.idempotency_key == idempotency_key
            )
            if existing:
                return existing[0]

        task = TaskRunDocument(
            task_type=task_type,
            execution_id=execution_id,
            idempotency_key=idempotency_key,
            payload_snapshot=payload_snapshot,
        )
        return await self.store.task_runs.create(task)

    async def mark_running(self, task_id: str) -> TaskRunDocument | None:
        return await self.store.task_runs.update(task_id, {"status": ExecutionState.RUNNING})

    async def mark_completed(self, task_id: str) -> TaskRunDocument | None:
        return await self.store.task_runs.update(task_id, {"status": ExecutionState.COMPLETED})

    async def mark_failed(self, task_id: str, reason: str) -> TaskRunDocument | None:
        task = await self.store.task_runs.get(task_id)
        if not task:
            return None

        retry_count = task.retry_count + 1
        can_retry = retry_count <= task.max_retries
        return await self.store.task_runs.update(
            task_id,
            {
                "status": ExecutionState.RETRYING if can_retry else ExecutionState.FAILED,
                "retry_count": retry_count,
                "next_retry_at": utc_now() + timedelta(minutes=retry_count * 5)
                if can_retry
                else None,
                "last_failure_reason": reason,
            },
        )

    async def retry(self, task_id: str) -> TaskRunDocument | None:
        task = await self.store.task_runs.get(task_id)
        if not task:
            return None
        if task.status != ExecutionState.RETRYING:
            return task
        return await self.store.task_runs.update(
            task_id,
            {
                "status": ExecutionState.PENDING,
                "next_retry_at": None,
                "last_failure_reason": None,
            },
        )

    async def execute_placeholder(self, task_id: str) -> TaskRunDocument | None:
        task = await self.mark_running(task_id)
        if not task:
            return None
        return await self.mark_completed(task_id)

    async def list_retryable(self) -> list[TaskRunDocument]:
        now = utc_now()
        return await self.store.task_runs.find(
            lambda task: task.status == ExecutionState.RETRYING
            and task.next_retry_at is not None
            and task.next_retry_at <= now
        )

    async def list_tasks(self) -> list[TaskRunDocument]:
        return await self.store.task_runs.list()
