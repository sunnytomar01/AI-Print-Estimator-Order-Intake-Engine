# Architecture Overview

- FastAPI backend (single source of truth for orders, pricing, validation, LLM calls)
- PostgreSQL for persistence
- n8n for workflows (CSR review, approvals, escalations, MIS handoff)
- React (Vite) + Tailwind frontend for intake and dashboard
- Docker Compose to run services locally

Key responsibilities:
- Backend: API surface, LLM calls, pricing, validation, DB writes, workflow triggers
- n8n: orchestrate human-in-the-loop and external integration tasks
- Frontend: order capture, status visualization, order detail view
