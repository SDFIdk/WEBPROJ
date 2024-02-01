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
from typing import List, Optional, Tuple, Union

from starlette.types import ASGIApp, Receive, Scope, Send

Headers = List[Tuple[bytes, bytes]]


class ProxyHeadersMiddleware:
    def __init__(self, app, trusted_hosts: Union[List[str], str] = "127.0.0.1") -> None:
        self.app = app
        if isinstance(trusted_hosts, str):
            self.trusted_hosts = {item.strip() for item in trusted_hosts.split(",")}
        else:
            self.trusted_hosts = set(trusted_hosts)
        self.always_trust = "*" in self.trusted_hosts

    def remap_headers(self, src: Headers, before: bytes, after: bytes) -> Headers:
        remapped = []
        before_value = None
        after_value = None
        for header in src:
            k, v = header
            if k == before:
                before_value = v
                continue
            elif k == after:
                after_value = v
                continue
            remapped.append(header)
        if after_value:
            remapped.append((before, after_value))
        elif before_value:
            remapped.append((before, before_value))
        return remapped

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] in ("http", "websocket"):

            client_addr: Optional[Tuple[str, int]] = scope.get("client")
            client_host = client_addr[0] if client_addr else None

            if self.always_trust or client_host in self.trusted_hosts:
                headers = dict(scope["headers"])
                if b"x-forwarded-proto" in headers:
                    # Determine if the incoming request was http or https based on
                    # the X-Forwarded-Proto header.
                    x_forwarded_proto = headers[b"x-forwarded-proto"].decode("latin1")
                    scope["scheme"] = x_forwarded_proto.strip()  # type: ignore[index]

                if b"x-forwarded-host" in headers:
                    # Setting scope["server"] is not enough because of https://github.com/encode/starlette/issues/604#issuecomment-543945716
                    scope["headers"] = self.remap_headers(
                        scope["headers"], b"host", b"x-forwarded-host"
                    )
                if b"x-forwarded-prefix" in headers:
                    x_forwarded_prefix = headers[b"x-forwarded-prefix"].decode("latin1")
                    scope["root_path"] = x_forwarded_prefix

        return await self.app(scope, receive, send)