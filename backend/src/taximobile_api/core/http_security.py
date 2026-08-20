"""Low-overhead response protections for the JSON API boundary."""

from __future__ import annotations

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class ResponseSecurityMiddleware:
    """Apply non-cache and browser hardening without buffering response bodies."""

    def __init__(self, app: ASGIApp, *, hsts_enabled: bool) -> None:
        self.app = app
        self.hsts_enabled = hsts_enabled

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def secured_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                # TaxiMobile responses contain identity, ride, location, or
                # financial state. Even operational and error responses are
                # cheap to regenerate and should not be retained by a shared
                # intermediary or browser history cache.
                headers["Cache-Control"] = "no-store"
                headers["Pragma"] = "no-cache"
                headers["X-Content-Type-Options"] = "nosniff"
                headers["Referrer-Policy"] = "no-referrer"
                headers["X-Frame-Options"] = "DENY"
                if self.hsts_enabled and scope.get("scheme") == "https":
                    # Do not claim subdomain ownership or preload eligibility.
                    headers["Strict-Transport-Security"] = "max-age=31536000"
            await send(message)

        await self.app(scope, receive, secured_send)
