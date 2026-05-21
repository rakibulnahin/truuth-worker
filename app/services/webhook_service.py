from app.repositories.store import RepositoryStore
from app.schemas.common import ExecutionState
from app.schemas.ops import WebhookEventDocument
from app.services.audit_service import AuditService


class WebhookService:
    def __init__(self, store: RepositoryStore) -> None:
        self.store = store
        self.audit = AuditService(store)

    async def receive_vendor_event(self, vendor: str, payload: dict) -> WebhookEventDocument:
        event = await self.store.webhook_events.create(
            WebhookEventDocument(
                vendor=vendor,
                event_type=payload.get("event_type", "vendor_callback"),
                status=ExecutionState.COMPLETED,
                payload=payload,
            )
        )

        external_execution_id = payload.get("external_execution_id")
        if external_execution_id:
            executions = await self.store.vendor_executions.find(
                lambda execution: execution.vendor == vendor
                and execution.external_execution_id == external_execution_id
            )
            for execution in executions:
                await self.store.vendor_executions.update(
                    execution.id,
                    {
                        "status": ExecutionState.COMPLETED,
                        "raw_response": {
                            **execution.raw_response,
                            "webhook_event_id": event.id,
                            "webhook_payload": payload,
                        },
                    },
                )

        await self.audit.log(
            operation="webhook_received",
            status="COMPLETED",
            vendor=vendor,
            event_type=event.event_type,
            external_execution_id=external_execution_id,
        )
        return event
