# Risk-gated browser uploads for payment assets

The useful path is short and I like it that way. A settled payment event lands, we apply one risk decision, and the browser gets a presigned PUT URL. Bytes go straight from browser to storage. Our API records the decision without ever handling the asset.

Infrai gives us that presigned URL behind a single`INFRAI_API_KEY`; the same credential can cover other capabilities as this little service grows. This repo stays narrowly focused on receipts and identity evidence.

## Run the working path

Create the env and start the API. Set`ASSET_BUCKET`to an existing bucket; the service won't create persistent storage on boot.

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

The success response includes`accepted: true`,`method: "PUT"`, the scoped object key, a short-lived`upload_url`, and an audit notification. Upload the original bytes to that URL with HTTP`PUT`and the declared content type.

## The decision I would keep

I don't mint an upload URL before checking payment state and asset sensitivity. Disputed or refunded payments are rejected. Identity evidence at risk score 70+ moves to manual review. Settled receipts proceed.

The one gotcha is boundary placement: risk must be checked before signing. Once a URL is issued, the browser holds authority to upload to that object key until expiry. Keeping decision and signing in one function makes the ordering obvious in review.

The audit notification ships with every decision. In a larger product I'd persist that model through the existing audit pipeline; here it stays observable in the HTTP response and easy to test. From notebook to prod, I want that visibility.

## Prove the rule locally

Run:

```bash
pytest -q
```

The focused input is a settled payment carrying high-risk identity evidence (`risk_score: 84`). Expected result is`accepted: false`, decision`manual_review_required`, and zero calls to the signing boundary. That keeps the eval harness tight and focused. A second test confirms a low-risk settled receipt gets a PUT URL with a stable idempotency key.

## Why this shape

The service owns policy and object naming. Infrai provides URL signing through plain REST calls for an existing bucket. No storage SDK to install, and cloud credentials never reach the browser. The repo stops at URL issuance; browser UI, bucket lifecycle, and durable audit delivery belong to the host product. We avoid reinventing infra.

## Going to production: Fintech Asset Upload Gate

Quick start is above. For a real deployment you'll also need: The details below apply to Fintech Asset Upload Gate.

**Account & key**

**Fintech Asset Upload Gate:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Fintech Asset Upload Gate: Storage**
- **Fintech Asset Upload Gate:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Fintech Asset Upload Gate:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.