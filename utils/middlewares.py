from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from utils.config import COOKIE_SECURE, CORS_ALLOWEDS


def register_middlewares(app: FastAPI) -> None:
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(OriginValidationMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOWEDS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Accept", "Accept-Language", "Content-Language", "Content-Type"],
    )


class OriginValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
            origin: str | None = request.headers.get("origin")

            if origin and origin not in _allowed_origins(request=request):
                return Response(status_code=403)

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
            "script-src 'self'; "
            "style-src 'self' https://lib.arvancloud.ir; "
            "font-src 'self' https://lib.arvancloud.ir data:; "
            "img-src 'self' data: http: https:",
        )
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")

        if COOKIE_SECURE:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

        return response


def _allowed_origins(request: Request) -> set[str]:
    host: str = request.headers.get("host", "")
    request_origin: str = "{}://{}".format(request.url.scheme, host) if host else ""
    return {origin for origin in [*CORS_ALLOWEDS, request_origin] if origin}
