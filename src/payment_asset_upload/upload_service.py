from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from .upload_policy import AssetKind, PaymentState, decide_upload


class StoragePort(Protocol):
    async def presign_put(
        self, bucket: str, key: str, *, content_type: str, max_bytes: int, idempotency_key: str
    ) -> dict[str, object]: ...


@dataclass
class PaymentAssetRequest:
    payment_event_id: str
    account_id: str
    payment_state: PaymentState
    risk_score: int
    asset_kind: AssetKind
    content_type: str
    size_bytes: int

    def __post_init__(self) -> None:
        self.payment_state = PaymentState(self.payment_state)
        self.asset_kind = AssetKind(self.asset_kind)
        if not 1 <= len(self.payment_event_id) <= 80:
            raise ValueError("payment_event_id must contain 1 to 80 characters")
        if not 1 <= len(self.account_id) <= 80:
            raise ValueError("account_id must contain 1 to 80 characters")
        if not 0 <= self.risk_score <= 100:
            raise ValueError("risk_score must be between 0 and 100")
        if self.content_type not in {"image/png", "image/jpeg", "application/pdf"}:
            raise ValueError("unsupported content_type")
        if not 0 < self.size_bytes <= 10_000_000:
            raise ValueError("size_bytes must be between 1 and 10000000")


@dataclass
class AuditNotification:
    event: str
    payment_event_id: str
    account_id: str
    decision: str
    recorded_at: datetime


@dataclass
class PaymentAssetResult:
    accepted: bool
    audit: AuditNotification
    upload_url: str | None = None
    method: str | None = None
    object_key: str | None = None


async def authorize_asset_upload(
    request: PaymentAssetRequest, storage: StoragePort, bucket: str
) -> PaymentAssetResult:
    decision = decide_upload(request.payment_state, request.risk_score, request.asset_kind)
    audit = AuditNotification(
        event="payment_asset_upload_decided",
        payment_event_id=request.payment_event_id,
        account_id=request.account_id,
        decision=decision.code,
        recorded_at=datetime.now(UTC),
    )
    if not decision.allowed:
        return PaymentAssetResult(accepted=False, audit=audit)

    object_key = f"{request.account_id}/{request.payment_event_id}/{request.asset_kind.value}"
    signed = await storage.presign_put(
        bucket,
        object_key,
        content_type=request.content_type,
        max_bytes=request.size_bytes,
        idempotency_key=f"asset:{request.payment_event_id}:{request.asset_kind.value}",
    )
    return PaymentAssetResult(
        accepted=True,
        upload_url=str(signed["url"]),
        method="PUT",
        object_key=object_key,
        audit=audit,
    )
