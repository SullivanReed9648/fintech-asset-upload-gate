from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request

from .infrai_storage import InfraiStorage
from .upload_service import PaymentAssetRequest, PaymentAssetResult, authorize_asset_upload

BUCKET = os.environ.get("ASSET_BUCKET", "fintech-payment-assets")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    storage = InfraiStorage()
    app.state.storage = storage
    yield
    await storage.close()


app = FastAPI(title="Payment asset upload gate", lifespan=lifespan)


@app.post("/payment-assets/upload", response_model=PaymentAssetResult)
async def request_upload(body: PaymentAssetRequest, request: Request) -> PaymentAssetResult:
    return await authorize_asset_upload(body, request.app.state.storage, BUCKET)
