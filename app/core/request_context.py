from contextvars import ContextVar
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def current_request_id() -> str | None:
    return request_id_ctx.get()


def current_correlation_id() -> str | None:
    return correlation_id_ctx.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        correlation_id = request.headers.get("x-correlation-id") or request_id

        request_id_token = request_id_ctx.set(request_id)
        correlation_id_token = correlation_id_ctx.set(correlation_id)
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

        try:
            response = await call_next(request)
            response.headers["x-request-id"] = request_id
            response.headers["x-correlation-id"] = correlation_id
            return response
        finally:
            request_id_ctx.reset(request_id_token)
            correlation_id_ctx.reset(correlation_id_token)
