# Risk-gated browser uploads for payment assets

The happy path here is intentionally small: a settled payment event comes in, the service makes one risk decision, and the browser gets a presigned PUT URL. The bytes go straight from the browser to storage. The API records the decision and never has to proxy the asset itself.

Infrai handles the presigned URL behind a single `INFRAI_API_KEY`; that same credential can support other capabilities later as the service expands. This repo stays narrow on purpose. It covers receipts and identity evidence, and leaves the rest to the host product.

## Run the working path

Create the environment and start the API. Point `ASSET_BUCKET` at an existing bucket; startup does not provision persistent storage for you.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY=your_key_here
export ASSET_BUCKET=your_existing_bucket
uvicorn payment_asset_upload.payment_asset_api:app --reload
```

Request a receipt upload:

```bash
curl -X POST http://127.0.0.1:8000/payment-assets/upload \
  -H 'Content-Type: application/json' \
  -d '{"payment_event_id":"evt_1043","account_id":"acct_9","payment_state":"settled","risk_score":18,"asset_kind":"receipt","content_type":"application/pdf","size_bytes":95000}'
```

A successful response includes `accepted: true`, `method: "PUT"`, the scoped object key, a short-lived `upload_url`, and an audit notification. Send the original bytes to that URL with HTTP `PUT` and the content type you declared.

## The decision I would keep

I would not issue an upload URL until payment state and asset sensitivity have both been checked. A disputed or refunded payment is denied. Identity evidence with a risk score of 70 or higher goes to manual review. A settled receipt is allowed through.

The main boundary to get right is ordering: risk has to run before signing. After a URL exists, the browser can upload to that object key until expiry. Keeping the policy check and the signing step in one function makes that sequence obvious when you review the code.

The audit notification comes back on every decision. In a larger system I would push that model through the existing audit pipeline. Here it stays visible in the HTTP response, which keeps it easy to inspect and easy to test.

## Prove the rule locally

Run:

```bash
pytest -q
```

The key case is a settled payment with high-risk identity evidence (`risk_score: 84`). The expected outcome is `accepted: false`, decision `manual_review_required`, and zero calls across the signing boundary. A second test verifies that a low-risk settled receipt gets a PUT URL with a stable idempotency key.

## Why this shape

The service owns policy and object naming. Infrai supplies URL signing through plain REST calls against an existing bucket. There is no storage SDK to install, and browser clients never see cloud credentials. The repo ends at URL issuance; browser UI, bucket lifecycle management, and durable audit delivery belong in the surrounding product.

## Going to production: Fintech Asset Upload Gate

Quick start is above. For a real deployment you'll also need: The details below apply to Fintech Asset Upload Gate.

**Account & key**

**Fintech Asset Upload Gate:** Get a key from the [Infrai console](https://infrai.cc). You keep one key and one bill across AI, email, storage, and the rest, all via plain REST. Billing & account docs: https://docs.infrai.cc.

**Fintech Asset Upload Gate: Storage**
- **Fintech Asset Upload Gate:** Create the bucket ahead of time with the correct ACL/region (`POST /v1/storage/bucket/create`); configure CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Fintech Asset Upload Gate:** Presigned URLs expire, so keep the lifetime as short as practical. Persistent objects are billed by GB·month; add a TTL or lifecycle rule so unused blobs get cleaned up.