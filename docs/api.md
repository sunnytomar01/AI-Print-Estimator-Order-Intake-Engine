# API Documentation

This document lists the main backend endpoints used by the frontend and n8n workflows.

## POST /intake/order
Accepts multipart form-data:
- `text` (string) - free text order description
- `email_body` (string) - optional email body
- `file` (PDF or image) - optional file upload
- `email` (string) - optional customer email

Returns: `{ "order_id": int, "issues": [...], "raw_text": "..." }` (201)

Notes:
- PDFs will be text-extracted (`app.utils.pdf_reader.extract_text_from_pdf`).
- Images will be OCR'd and checked for DPI; low DPI may add `low_resolution` to returned issues.

## POST /estimate
JSON body: `{ "order_id": int, "raw_text": "...", "customer_email": "optional@example.com" }`
Returns: `{ "order_id": int, "spec": {...}, "validation": {...}, "pricing": {...} }`

Behavior:
- The endpoint parses `raw_text` via `LLMSpecParser` (heuristic fallback when no OpenAI key is present).
- Validation follows `Validator` rules (`auto_approved`, `needs_review`, `rejected`).
- The LLM can include explicit override tokens in the text (e.g. "send to auto_approved") — these are detected deterministically.
- Pricing is produced by `PriceEngine` and stored on the Order record.
- A single DB commit is used to persist the final result; a workflow is triggered in n8n with a short payload containing `order_id`, `decision`, `price`, and `issues`.

## PUT /orders/{order_id}
Used by n8n or MIS tasks to update an order's status or price. Body should include `status` and optionally `price` and `issues`.

## POST /workflow/update
A backwards-compatible endpoint (used by some workflows) which accepts a payload with `order_id`, `decision` or `status`, `price`, `issues`, and `email`.

## Dashboard endpoints
- `GET /dashboard/summary` — Returns total orders, revenue, and pending count.
- `GET /dashboard/orders` — Returns list of orders with summary fields.
- `GET /dashboard/stats` — Returns counts grouped by status.

## Environment vars affecting behavior
- `OPENAI_API_KEY` — Optional. If set, the backend will attempt to use OpenAI ChatCompletion for parsing/decisions.
- `OPENAI_MODEL` — Optional. Default `gpt-3.5-turbo`.
- `N8N_WEBHOOK_URL` — The default webhook path used by `WorkflowClient` (e.g. `http://n8n:5678/webhook/ai-estimator` in compose).

## n8n / Webhook notes
- Import `n8n/workflows.json` and **activate** the workflow in the UI to register `/webhook` paths.
- The workflow will call `/orders/{id}` (PUT) and `/mis/orders` (POST) as part of its flow.
- If testing in n8n **Test** mode, use `/webhook-test/<path>` instead of `/webhook/<path>`; the `WorkflowClient` tries `/webhook` and `/webhook-test` variants.

