import requests
import logging
import os
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

DEFAULT_N8N = os.getenv("N8N_WEBHOOK_URL", "http://n8n:5678/webhook-test/ai-estimator")

class WorkflowClient:
    def __init__(self, webhook_url: str = None, max_retries: int = 3):
        self.webhook = webhook_url or DEFAULT_N8N
        self.max_retries = max_retries
        logger.debug("WorkflowClient initialized with webhook=%s max_retries=%s", self.webhook, self.max_retries)

    def trigger(self, payload: Dict[str, Any]) -> bool:
        headers = {"Content-Type": "application/json"}
        # add idempotency key to avoid duplicate processing in n8n
        if "order_id" in payload:
            headers["Idempotency-Key"] = f"order-{payload['order_id']}"

        # prepare candidate webhook URLs (helpful for backward compatibility)
        candidates = [self.webhook]
        if 'ai-print-workflow' in self.webhook and 'ai-estimator' not in self.webhook:
            candidates.append(self.webhook.replace('ai-print-workflow', 'ai-estimator'))
        elif 'ai-estimator' in self.webhook and 'ai-print-workflow' not in self.webhook:
            candidates.append(self.webhook.replace('ai-estimator', 'ai-print-workflow'))
        else:
            # generic fallbacks
            base = self.webhook.rstrip('/')
            if not base.endswith('/ai-estimator'):
                candidates.append(base + '/ai-estimator')
            if not base.endswith('/ai-print-workflow'):
                candidates.append(base + '/ai-print-workflow')

        # Add /webhook vs /webhook-test variants and localhost fallback for local testing
        extra = []
        for c in list(candidates):
            if '/webhook-test/' in c and '/webhook/' not in c:
                extra.append(c.replace('/webhook-test/', '/webhook/'))
            if '/webhook/' in c and '/webhook-test/' not in c:
                extra.append(c.replace('/webhook/', '/webhook-test/'))
            # localhost fallback for dev (useful when backend runs outside compose)
            if '://n8n' in c:
                extra.append(c.replace('://n8n', '://localhost'))
        candidates.extend(extra)

        # Ensure uniqueness and preserve order
        seen = set()
        candidates = [c for c in candidates if not (c in seen or seen.add(c))]

        for attempt in range(1, self.max_retries + 1):
            for url in candidates:
                try:
                    logger.debug("Triggering workflow attempt=%s url=%s", attempt, url)
                    resp = requests.post(url, json=payload, timeout=5, headers=headers)
                    resp.raise_for_status()
                    logger.info("Triggered workflow url=%s status=%s", url, resp.status_code)
                    return True
                except Exception as e:
                    logger.warning("Attempt %s url=%s: Failed to trigger workflow: %s", attempt, url, e)
                    # try next url or retry
            if attempt < self.max_retries:
                time.sleep(0.5 * attempt)
                continue
            logger.exception("All attempts to trigger workflow failed after trying candidates: %s", candidates)
            return False
