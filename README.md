# AI Print Estimator

Scaffold for an AI-driven print estimator and order intake engine.

Services:
- FastAPI backend
- PostgreSQL
- n8n
- React frontend (Vite + Tailwind)

Quick start:
1. Copy configuration: `cp .env.example .env` and edit values if needed.
2. Start services: `docker compose up --build`
3. Backend: http://localhost:${BACKEND_PORT:-8000}
4. Frontend: http://localhost:${FRONTEND_PORT:-3000}
5. n8n: http://localhost:5678

Optional: OpenAI
- To enable OpenAI-powered parsing/decisioning set `OPENAI_API_KEY` in your `.env` and optionally `OPENAI_MODEL` (default: `gpt-3.5-turbo`). The system falls back to a deterministic local parser when no key is set.

Estimate endpoint notes
- `POST /estimate` accepts an optional `customer_email` which will be persisted on the Order and forwarded to workflows where applicable.
- The endpoint performs parsing, validation, and pricing and persists the final order once (single commit) to reduce races and duplicate writes.

n8n webhooks & `N8N_WEBHOOK_URL`
- `N8N_WEBHOOK_URL` defaults to `http://n8n:5678/webhook/ai-estimator` in the compose setup. If you use older workflows that reference `ai-print-workflow`, either set `N8N_WEBHOOK_URL` to that path or update the workflow webhook name.


Run tests (locally):
- python -m pip install -r backend/requirements-dev.txt
- cd backend && pytest -q

How to test endpoints (examples):

1) Text-only intake (returns order_id and raw_text):

curl -X POST "http://localhost:${BACKEND_PORT:-8000}/intake/order" \
  -F "text=Please print 250 flyers 210x297mm C300 4/0 lamination 3 days"

2) File upload (PDF):

curl -X POST "http://localhost:${BACKEND_PORT:-8000}/intake/order" \
  -F "file=@/path/to/sample.pdf"

3) Run estimation for a created order (use order_id from intake response):

curl -X POST "http://localhost:${BACKEND_PORT:-8000}/estimate" \
  -H "Content-Type: application/json" \
  -d '{"order_id": 1, "raw_text": "Please print 250 flyers 210x297mm C300 4/0 lamination 3 days"}'

4) Dashboard:

- Summary: GET http://localhost:${BACKEND_PORT:-8000}/dashboard/summary
- Orders: GET http://localhost:${BACKEND_PORT:-8000}/dashboard/orders
- Stats: GET http://localhost:${BACKEND_PORT:-8000}/dashboard/stats

n8n workflows:
- Import `n8n/workflows.json` in the n8n UI (Workflows → Import).
- After import: *activate* the workflow (Open it and toggle **Active**). Only active workflows register webhook paths.
- Open the imported workflow and edit the `Workflow Configuration` node to set these values (local dev):
  ```ini
  backendApiUrl = http://localhost:8000
  taskSystemUrl = http://localhost:8000/csr/tasks
  misApiUrl     = http://localhost:8000/mis/orders
  csrEmail      = csr@test.com
  managerEmail  = manager@test.com
  opsEmail      = ops@test.com
  ```
- Notes about testing webhooks: n8n exposes active webhook paths under `/webhook/<path>` when executed normally, and under `/webhook-test/<path>` when you run a workflow in **Test** mode. If a webhook call returns 404, confirm the workflow is *active* and use the correct `/webhook` vs `/webhook-test` URL.
- The workflow's order-update nodes PUT to `/orders/<id>` and MIS handoff nodes POST to `/mis/orders` (both on `backendApiUrl`).
- Test the workflow by triggering the webhook path shown in the workflow UI (e.g. `/webhook/ai-estimator`).

**n8n Setup (important)**
1) Open the workflow in the n8n editor and edit the **Workflow Configuration** (Set node). Replace placeholders with these values depending on your environment:

- If you run **n8n inside Docker compose** (recommended for this repo), use the *service hostnames* so containers can reach each other:
```
backendApiUrl = http://backend:8000
taskSystemUrl = http://backend:8000/csr/tasks
misApiUrl     = http://backend:8000/mis/orders
csrEmail      = csr@test.com
managerEmail  = manager@test.com
opsEmail      = ops@test.com
```

- If you run **n8n outside Docker on your host** and backend is on the host, use localhost or host.docker.internal (depending on your OS):
```
backendApiUrl = http://localhost:8000  # or http://host.docker.internal:8000 on some Docker setups
misApiUrl     = http://localhost:8000/mis/orders
```

2) Fix JSON body bug in **Create CSR Task** node: change

```
"issues": {{ $json.issues.join(', ') }}
```

to

```
"issues": "{{ $json.issues.join(', ') }}"
```

(Otherwise the JSON body becomes invalid).

**Tip:** Docker Compose default `N8N_WEBHOOK_URL` is set to `http://n8n:5678/webhook/ai-estimator`. If you need to keep an older workflow that uses `ai-print-workflow`, set `N8N_WEBHOOK_URL` in your `.env` to that path or import the workflow and rename its webhook to `ai-estimator`.

Notes:
- Docker Compose reads `.env` in the project root; edit it before `docker compose up`.
- To view backend logs: `docker compose logs -f backend` (useful for debugging intake/estimate flows).
- To run backend locally without Docker: set `DATABASE_URL` to a running Postgres and run `uvicorn app.main:app --reload`.

