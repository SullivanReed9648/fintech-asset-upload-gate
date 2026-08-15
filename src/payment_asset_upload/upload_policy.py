from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PaymentState(StrEnum):
    SETTLED = "settled"
    DISPUTED = "disputed"
    REFUNDED = "refunded"


class AssetKind(StrEnum):
    RECEIPT = "receipt"
    IDENTITY_EVIDENCE = "identity_evidence"


@dataclass(frozen=True)
class UploadDecision:
    allowed: bool
    code: str


def decide_upload(payment_state: PaymentState, risk_score: int, asset_kind: AssetKind) -> UploadDecision:
    if payment_state is not PaymentState.SETTLED:
        return UploadDecision(False, "payment_not_settled")
    if asset_kind is AssetKind.IDENTITY_EVIDENCE and risk_score >= 70:
        return UploadDecision(False, "manual_review_required")
    return UploadDecision(True, "upload_authorized")
