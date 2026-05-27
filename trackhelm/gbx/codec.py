from __future__ import annotations

from typing import Any
import xmlrpc.client


class XmlRpcCodec:
    """
    XML-RPC codec for TMNF GBXRemote.
    """

    @staticmethod
    def encode(method: str, params: list[Any]) -> bytes:
        return xmlrpc.client.dumps(
            tuple(params), methodname=method, allow_none=True, encoding="utf-8"
        ).encode()

    @staticmethod
    def decode(payload: bytes) -> tuple[str | None, Any]:
        params, method = xmlrpc.client.loads(payload)

        if method:
            return method, list(params)

        return None, params[0] if params else None
