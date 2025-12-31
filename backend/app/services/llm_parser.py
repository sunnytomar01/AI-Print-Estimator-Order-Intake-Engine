from typing import Dict, Any, Optional
import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """
You are a strict JSON extractor. Given the following order text, output EXACTLY a JSON object (no explanations) matching schema:
{
  "product_type": "",
  "quantity": 0,
  "size": "",
  "paper_type": "",
  "color": "",
  "finishing": [],
  "turnaround_days": 0,
  "rush": false,
  "missing_fields": []
}
Ensure fields are present; for missing fields, list their names in "missing_fields".
Respond ONLY with JSON (no markdown, backticks or commentary). If you cannot find a field, put null or an empty list and include the field name in "missing_fields".
Use deterministic parsing (temperature=0).
Only output JSON object — nothing else.

Text:
"""

# Pre-compiled override patterns for deterministic checks
OVERRIDE_REVIEW_RE = re.compile(r"\b(send(?: this)?(?: to)?|please send(?: this)?(?: to)?)\s+(needs[_\-\s]?review|needs review|review)\b", re.I)
OVERRIDE_APPROVE_RE = re.compile(r"\b(send(?: this)?(?: to)?|please send(?: this)?(?: to)?)\s+(auto[_\-\s]?approved|auto[_\-\s]?approve|approved)\b", re.I)
OVERRIDE_REJECT_RE = re.compile(r"\b(send(?: this)?(?: to)?|please send(?: this)?(?: to)?)\s+(rejected|reject(?:ed)?)\b", re.I)

# Optional OpenAI integration: if OPENAI_API_KEY is set in the environment, the parser will use OpenAI ChatCompletion
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
try:
    import openai
    HAVE_OPENAI = True
    if OPENAI_API_KEY:
        openai.api_key = OPENAI_API_KEY
except Exception:
    openai = None
    HAVE_OPENAI = False


class LLMSpecParser:
    """LLM-backed specification extractor.

    The parser expects a `client` object with a `chat` or `complete` interface returning text.
    In tests, provide a mock client that returns JSON text.
    """

    def __init__(self, client: Optional[object] = None):
        self.client = client

    def _default_parse(self, text: str) -> Dict[str, Any]:
        # Heuristic regex-based parser for local testing when an LLM is not available.
        # Extract common fields (quantity, size, paper, color, finishing, turnaround, rush).
        import re
        txt = (text or "").lower()

        # If the text looks like gibberish or is extremely short without keywords, flag missing critical fields
        if len(txt) < 30 and not any(k in txt for k in ("print", "flyer", "business", "card", "please", "brochure")):
            return {
                "product_type": None,
                "quantity": None,
                "size": None,
                "paper_type": None,
                "color": None,
                "finishing": [],
                "turnaround_days": None,
                "rush": None,
                "missing_fields": ["product_type", "quantity", "size"],
            }

        # Quantity (e.g., 'print 250' or '250 flyers')
        q_match = re.search(r"\b(\d{1,6})\b(?=\s*(?:pieces|pcs|flyers|cards|brochures|units)?)", txt)
        quantity = int(q_match.group(1)) if q_match else None

        # Size (e.g., 210x297 or 85x55mm)
        size_match = re.search(r"(\d{2,4}\s*[x×]\s*\d{2,4}(?:mm)?)", txt)
        size = size_match.group(1).replace(" ", "") if size_match else None

        # Paper type (C300, C350) and color (4/0, 4/4)
        paper_match = re.search(r"\b(c\d{3})\b", txt)
        paper = paper_match.group(1).upper() if paper_match else None
        color_match = re.search(r"\b(\d+/\d+)\b", txt)
        color = color_match.group(1) if color_match else None

        # finishing
        finishing = []
        if "lamination" in txt:
            finishing.append("lamination")
        if "spot uv" in txt or "spot_uv" in txt or "spotuv" in txt:
            finishing.append("spot_uv")
        if "die cut" in txt or "die_cut" in txt:
            finishing.append("die_cut")
        if not finishing:
            finishing = ["none"]

        # turnaround days
        td_match = re.search(r"(\d{1,3})\s*(day|days)", txt)
        turnaround = int(td_match.group(1)) if td_match else None

        # rush detection
        rush = bool(re.search(r"\b(rush|urgent)\b", txt))

        missing = []
        if not quantity:
            missing.append("quantity")
        if not size:
            missing.append("size")
        if not paper:
            missing.append("paper_type")

        return {
            "product_type": "business_card" if "card" in txt else ("flyer" if "flyer" in txt or "flyers" in txt else None),
            "quantity": quantity or 100,
            "size": size or "85x55mm",
            "paper_type": paper or "C300",
            "color": color or "4/4",
            "finishing": finishing,
            "turnaround_days": turnaround or 3,
            "rush": rush,
            "missing_fields": missing,
        }

    def _call_client(self, prompt: str, text: Optional[str] = None) -> str:
        # If a client was explicitly provided (for testing), use it
        if self.client is not None:
            try:
                # Support a few common testing-client shapes
                if hasattr(self.client, "chat"):
                    resp = self.client.chat([{"role": "user", "content": prompt}])
                    # tests may return {"content": "..."} or OpenAI-like choices
                    if isinstance(resp, dict):
                        if "content" in resp:
                            return resp["content"]
                        if "choices" in resp and resp["choices"]:
                            c = resp["choices"][0]
                            return c.get("message", {}).get("content") or c.get("text") or str(resp)
                    return str(resp)
                elif hasattr(self.client, "complete"):
                    resp = self.client.complete(prompt)
                    return resp
                else:
                    return str(self.client(prompt))
            except Exception as e:
                logger.exception("LLM client call failed: %s", e)
                return json.dumps({"missing_fields": ["parse_error"]})

        # If OpenAI is available and API key is configured, use it
        if HAVE_OPENAI and OPENAI_API_KEY:
            try:
                logger.debug("Calling OpenAI model=%s", OPENAI_MODEL)
                messages = [
                    {"role": "system", "content": "You are a strict JSON-only extractor. Respond with JSON only."},
                    {"role": "user", "content": PROMPT_TEMPLATE + "\n" + prompt},
                ]
                resp = openai.ChatCompletion.create(model=OPENAI_MODEL, messages=messages, temperature=0)
                content = resp["choices"][0]["message"]["content"]
                return content
            except Exception as e:
                logger.exception("OpenAI call failed: %s", e)
                # fall through to default parser

        logger.debug("No LLM client or OpenAI available; using default parser")
        # Use the raw text (if provided) for the local heuristic parser to avoid parsing the prompt template
        return json.dumps(self._default_parse(text or prompt))

    def _clean_json_text(self, text: str) -> str:
        # Some LLMs may wrap JSON in backticks or markdown; try to extract the first {...}
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
        return text

    def _detect_override(self, txt: str) -> Optional[str]:
        """Detect explicit override tokens in free text and return decision token or None."""
        if OVERRIDE_REVIEW_RE.search(txt):
            logger.debug("Explicit override detected in text: needs_review")
            return "needs_review"
        if OVERRIDE_APPROVE_RE.search(txt):
            logger.debug("Explicit override detected in text: auto_approved")
            return "auto_approved"
        if OVERRIDE_REJECT_RE.search(txt):
            logger.debug("Explicit override detected in text: rejected")
            return "rejected"
        return None

    def parse(self, text: str) -> Dict[str, Any]:
        """Parse free text into structured spec using the configured LLM client.

        Returns a dict conforming to the schema; on parse errors, returns a dict with missing_fields populated.
        """
        prompt = PROMPT_TEMPLATE + "\n" + text
        raw = self._call_client(prompt, text)

        try:
            cleaned = self._clean_json_text(raw)
            spec = json.loads(cleaned)
        except Exception as e:
            logger.exception("Failed to parse LLM output to JSON: %s", e)
            return {"missing_fields": ["parse_error"]}

        # Enforce schema keys and defaults
        keys = ["product_type", "quantity", "size", "paper_type", "color", "finishing", "turnaround_days", "rush", "missing_fields"]
        for k in keys:
            if k not in spec:
                spec[k] = None if k != "finishing" and k != "missing_fields" else []

        # Ensure types
        if not isinstance(spec.get("finishing"), list):
            spec["finishing"] = [spec["finishing"]] if spec.get("finishing") else []
        if not isinstance(spec.get("missing_fields"), list):
            spec["missing_fields"] = [spec["missing_fields"]] if spec.get("missing_fields") else []

        return spec

    def decide(self, spec: Dict[str, Any], text: Optional[str] = None, full: bool = True) -> Optional[str]:
        """Decide order disposition.

        If full=True (default), return a decision string: 'auto_approved', 'needs_review', or 'rejected'.
        If full=False, only inspect the free text for explicit override tokens ("send to auto_approved", etc.) and return that token or None.
        """
        txt = (text or "").lower()

        # If only looking for explicit overrides, return them if present
        if not full:
            return self._detect_override(txt)

        # Try OpenAI when available for a full decision
        if HAVE_OPENAI and OPENAI_API_KEY:
            try:
                logger.debug("Calling OpenAI for decision model=%s", OPENAI_MODEL)
                messages = [
                    {"role": "system", "content": "You are a decision engine: answer with exactly one of: auto_approved, needs_review, rejected. Do not add explanation."},
                    {"role": "user", "content": "Spec: %s\nText: %s\n\nReturn one of: auto_approved, needs_review, rejected." % (json.dumps(spec), txt)},
                ]
                resp = openai.ChatCompletion.create(model=OPENAI_MODEL, messages=messages, temperature=0)
                content = resp["choices"][0]["message"]["content"].strip().lower()
                for token in ("auto_approved", "needs_review", "rejected"):
                    if token in content:
                        return token
                return content.split()[0]
            except Exception as e:
                logger.exception("OpenAI decision call failed: %s", e)

        # Deterministic fallback (mimic Validator priorities)
        # Allow explicit text overrides if present (use compiled regex helper)
        explicit = self._detect_override(txt)
        if explicit:
            return explicit

        # If missing fields -> needs_review
        if spec.get("missing_fields"):
            return "needs_review"

        # Rejected indicators (invalid size, unsupported finishing, non-positive quantity)
        finishing = spec.get("finishing") or []
        if not isinstance(finishing, list):
            finishing = [finishing]
        for f in finishing:
            if f not in ("lamination", "spot_uv", "die_cut", "none"):
                return "rejected"

        try:
            q = int(spec.get("quantity") or 0)
            if q <= 0:
                return "rejected"
        except Exception:
            return "needs_review"

        if "for free" in txt or "free" in txt:
            return "rejected"

        return "auto_approved"
