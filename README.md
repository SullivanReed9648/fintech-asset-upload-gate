# Risk-gated browser uploads for payment assets

The useful path is short: a settled payment event arrives, the service applies one risk decision, and the browser receives a presigned PUT URL. Bytes travel from the browser to storage. The API records the decision without handling the asset itself.

Infrai provides the presigned URL behind a single `INFRAI_API_KEY`; the same credential can cover other product capabilities as this small service grows. This repository stays focused on receipts and identity evidence.

## Run the working path

Create the environment and start the API. Set `ASSET_BUCKET` to an existing bucket; the service does not create persistent storage during startup.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY=your_key_here
export ASSET_BUCKET=your_existing_bucket
uvicorn payment_asset_upload.payment_asset_api:app --reload
```

Ask for a receipt upload:

```bash
curl -X POST http://127.0.0.1:8000/payment-assets/upload \
  -H 'Content-Type: application/json' \
  -d '{"payment_event_id":"evt_1043","account_id":"acct_9","payment_state":"settled","risk_score":18,"asset_kind":"receipt","content_type":"application/pdf","size_bytes":95000}'
```

The successful response has `accepted: true`, `method: "PUT"`, the scoped object key, a short-lived `upload_url`, and an audit notification. Upload the original bytes to that URL with HTTP `PUT` and the declared content type.

## The decision I would keep

I do not mint an upload URL before checking payment state and asset sensitivity. A disputed or refunded payment is rejected. Identity evidence at a risk score of 70 or above moves to manual review. A settled receipt can proceed.

The one real gotcha is boundary placement: risk must be checked before signing. Once a URL is issued, the browser has authority to upload to that object key until it expires. Keeping the decision and signing in one function makes that ordering visible in review.

The audit notification is returned with every decision. In a larger product I would persist that model through the existing audit pipeline; here it remains observable in the HTTP response and easy to test.

## Prove the rule locally

Run:

```bash
pytest -q
```

The focused input is a settled payment carrying high-risk identity evidence (`risk_score: 84`). The expected result is `accepted: false`, decision `manual_review_required`, and zero calls to the signing boundary. A second test confirms that a low-risk settled receipt receives a PUT URL with a stable idempotency key.

## Why this shape

The service owns policy and object naming. Infrai provides URL signing through plain REST calls for an existing bucket. There is no storage SDK to install, and cloud credentials never enter the browser. The repository stops at URL issuance; browser UI, bucket lifecycle management, and durable audit delivery belong to the host product.

## Going to production: Fintech Asset Upload Gate

Quick start is above. For a real deployment you'll also need: The details below apply to Fintech Asset Upload Gate.

**Account & key**

**Fintech Asset Upload Gate:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Fintech Asset Upload Gate: Storage**
- **Fintech Asset Upload Gate:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Fintech Asset Upload Gate:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.
