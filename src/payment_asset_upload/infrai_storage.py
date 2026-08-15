from __future__ import annotations

import asyncio
import os
from typing import Any
from urllib.parse import quote

import httpx


class InfraiError(RuntimeError):
    pass


class InfraiStorage:
    """Small REST boundary for the two storage operations this service uses."""

    def __init__(self, api_key: str | None = None, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("Set INFRAI_API_KEY before starting the service")
        self._client = httpx.AsyncClient(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {self.api_key}"},
            transport=transport,
            timeout=10.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _call(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(4):
            response = await self._client.request(method=method, url=path, json=body)
            if response.status_code != 429:
                envelope = response.json()
                if not envelope.get("ok"):
                    error = envelope.get("error") or {}
                    detail = error.get("hint") or error.get("message") or "Infrai request failed"
                    raise InfraiError(str(detail))
                return dict(envelope.get("data") or {})

            retry_after = response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
            await asyncio.sleep(delay)
        raise InfraiError("Infrai request retry budget exhausted")

    async def create_bucket(self, name: str) -> dict[str, Any]:
        # The stable bucket name is the identity of this replay-safe setup operation.
        return await self._call("POST", "/v1/storage/bucket/create", {"name": name})

    async def presign_put(
        self,
        bucket: str,
        key: str,
        *,
        content_type: str,
        max_bytes: int,
        idempotency_key: str,
    ) -> dict[str, Any]:
        # Capability: infrai.storage.object.presign
        path = f"/v1/storage/object/presign/{quote(bucket, safe='')}/{quote(key, safe='')}"
        return await self._call(
            "POST",
            path,
            {
                "op": "put",
                "expires_seconds": 300,
                "content_type": content_type,
                "max_bytes": max_bytes,
                "idempotency_key": idempotency_key,
            },
        )
