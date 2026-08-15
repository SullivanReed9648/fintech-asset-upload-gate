from __future__ import annotations

import asyncio

from payment_asset_upload.upload_service import PaymentAssetRequest, authorize_asset_upload


class RecordingStorage:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def presign_put(self, bucket: str, key: str, **options: object) -> dict[str, object]:
        self.calls.append({"bucket": bucket, "key": key, **options})
        return {"url": "https://uploads.example/signed-payment-asset"}


def test_high_risk_identity_asset_requires_review_without_signing() -> None:
    storage = RecordingStorage()
    request = PaymentAssetRequest(
        payment_event_id="evt_1042",
        account_id="acct_9",
        payment_state="settled",
        risk_score=84,
        asset_kind="identity_evidence",
        content_type="image/png",
        size_bytes=240_000,
    )

    result = asyncio.run(authorize_asset_upload(request, storage, "payment-assets"))

    assert result.accepted is False
    assert result.audit.decision == "manual_review_required"
    assert storage.calls == []


def test_settled_receipt_gets_scoped_put_url() -> None:
    storage = RecordingStorage()
    request = PaymentAssetRequest(
        payment_event_id="evt_1043",
        account_id="acct_9",
        payment_state="settled",
        risk_score=18,
        asset_kind="receipt",
        content_type="application/pdf",
        size_bytes=95_000,
    )

    result = asyncio.run(authorize_asset_upload(request, storage, "payment-assets"))

    assert result.accepted is True
    assert result.method == "PUT"
    assert result.object_key == "acct_9/evt_1043/receipt"
    assert storage.calls[0]["idempotency_key"] == "asset:evt_1043:receipt"
