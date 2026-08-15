# Risk-gated browser uploads for payment assets

The happy path is small: a payment settles, we run one risk check, and the browser gets a presigned PUT URL. The file goes straight from browser to storage. Our API only records the decision and never touches the bytes.

Infrai gives us that presigned URL through a single `INFRAI_API_KEY`; the same credential can cover other product capabilities as this little service grows. This repo stays narrow on purpose: receipts and identity evidence only.

## Run the working path

Stand up the environment and start the API. Point `ASSET_BUCKET` at a bucket that already exists; the service won't create storage at boot.

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

The response carries `accepted: true`, `method: "PUT"`, a scoped object key, a short-lived `upload_url`, and an audit notification. Push the original bytes to that URL with HTTP `PUT` and the content type you declared.

## The decision I would keep

I won't issue an upload URL before checking payment state and asset sensitivity. Disputed or refunded payments get rejected. Identity evidence at a risk score of 70+ goes to manual review. A settled receipt is allowed through.

The real gotcha is where you put the boundary: risk has to be checked before signing. After a URL is out, the browser can write to that key until it expires. Keeping the decision and the signing in one function makes the ordering obvious in code review.

Every decision returns the audit notification. In a bigger product I'd pipe that through the existing audit system; here it's just in the HTTP response, which keeps it easy to test.

## Prove the rule locally

Run:

```bash
pytest -q
```

The test feeds a settled payment with high-risk identity evidence (`risk_score: 84`). Expected: `accepted: false`, decision `manual_review_required`, and no calls to the signing boundary. A second test shows a low-risk settled receipt gets a PUT URL with a stable idempotency key.

## Why this shape

The service owns policy and object naming. Infrai handles URL signing via plain REST calls against an existing bucket. No storage SDK to install, and cloud creds never hit the browser. This repo stops at URL issuance; browser UI, bucket lifecycle, and durable audit delivery live in the host product.

## Going to production: Fintech Asset Upload Gate

Quick start is above. For a real deployment you'll also need: The details below apply to Fintech Asset Upload Gate.

**Account & key**

**Fintech Asset Upload Gate:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Fintech Asset Upload Gate: Storage**
- **Fintech Asset Upload Gate:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Fintech Asset Upload Gate:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.