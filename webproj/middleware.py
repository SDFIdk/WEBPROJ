"""
This middleware can be used when a known proxy is fronting the application,
and is trusted to be properly setting the `X-Forwarded-Proto`,
`X-Forwarded-Host` and `x-forwarded-prefix` headers with.

Modifies the `host`, 'root_path' and `scheme` information.

https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers#Proxies

Original source: https://github.com/encode/uvicorn/blob/master/uvicorn/middleware/proxy_headers.py
Altered to accomodate x-forwarded-host instead of x-forwarded-for
Altered: 27-01-2022
"""
import re
from typing import List, Optional, Tuple, Union
from http.client import HTTP_PORT, HTTPS_PORT
from starlette.types import ASGIApp, Receive, Scope, Send

Headers = List[Tuple[bytes, bytes]]


class ProxyHeaderMiddleware:
    """Account for forwarding headers when deriving base URL.

    Prioritise standard Forwarded header, look for non-standard X-Forwarded-* if missing.
    Default to what can be derived from the URL if no headers provided. Middleware updates
    the host header that is interpreted by starlette when deriving Request.base_url.
    """

    def __init__(self, app: ASGIApp):
        """Create proxy header middleware."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Call from stac-fastapi framework."""
        if scope["type"] == "http":
            proto, domain, port = self._get_forwarded_url_parts(scope)
            scope["scheme"] = proto
            if domain is not None:
                port_suffix = ""
                if port is not None:
                    if (proto == "http" and port != HTTP_PORT) or (
                        proto == "https" and port != HTTPS_PORT
                    ):
                        port_suffix = f":{port}"
                scope["headers"] = self._replace_header_value_by_name(
                    scope,
                    "host",
                    f"{domain}{port_suffix}",
                )
        await self.app(scope, receive, send)

    def _get_forwarded_url_parts(self, scope: Scope) -> Tuple[str]:
        proto = scope.get("scheme", "http")
        header_host = self._get_header_value_by_name(scope, "host")
        if header_host is None:
            domain, port = scope.get("server")
        else:
            header_host_parts = header_host.split(":")
            if len(header_host_parts) == 2:
                domain, port = header_host_parts
            else:
                domain = header_host_parts[0]
                port = None
        forwarded = self._get_header_value_by_name(scope, "forwarded")
        if forwarded is not None:
            parts = forwarded.split(";")
            for part in parts:
                if len(part) > 0 and re.search("=", part):
                    key, value = part.split("=")
                    if key == "proto":
                        proto = value
                    elif key == "host":
                        host_parts = value.split(":")
                        domain = host_parts[0]
                        try:
                            port = int(host_parts[1]) if len(host_parts) == 2 else None
                        except ValueError:
                            # ignore ports that are not valid integers
                            pass
        else:
            proto = self._get_header_value_by_name(scope, "x-forwarded-proto", proto)
            port_str = self._get_header_value_by_name(scope, "x-forwarded-port", port)
            try:
                port = int(port_str) if port_str is not None else None
            except ValueError:
                # ignore ports that are not valid integers
                pass

        return (proto, domain, port)

    def _get_header_value_by_name(
        self, scope: Scope, header_name: str, default_value: str = None
    ) -> str:
        headers = scope["headers"]
        candidates = [
            value.decode() for key, value in headers if key.decode() == header_name
        ]
        return candidates[0] if len(candidates) == 1 else default_value

    @staticmethod
    def _replace_header_value_by_name(
        scope: Scope, header_name: str, new_value: str
    ) -> List[Tuple[str]]:
        return [
            (name, value)
            for name, value in scope["headers"]
            if name.decode() != header_name
        ] + [(str.encode(header_name), str.encode(new_value))]
