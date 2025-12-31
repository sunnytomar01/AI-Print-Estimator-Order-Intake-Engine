from typing import Dict, Any, List, Optional

SUPPORTED_FINISHING = {"lamination", "spot_uv", "die_cut", "none"}


class Validator:
    """Validation logic for order specs.

    Rules:
    - missing_fields -> needs_review
    - free/for free or clearly insufficient specs -> rejected
    - min_dpi < 300 -> needs_review
    - invalid size format or zero/negative -> rejected
    - turnaround_days <=0 or unreasonably large (>365) -> rejected
    - unsupported finishing -> rejected

    Deterministic: issues are returned sorted and decision is deterministic based on priority of errors.
    """

    def _add_issue(self, issues: List[str], issue: str) -> None:
        if issue not in issues:
            issues.append(issue)

    def validate(self, spec: Dict[str, Any], text: Optional[str] = None) -> Dict[str, Any]:
        issues: List[str] = []

        txt = (text or "").lower()

        # Missing fields reported by LLM
        missing = spec.get("missing_fields", []) or []
        if missing:
            self._add_issue(issues, "missing_fields:" + ",".join(sorted(map(str, missing))))

        # If the text explicitly mentions free pricing -> reject
        if "for free" in txt or " free " in txt or txt.strip().endswith("free"):
            self._add_issue(issues, "free_pricing")

        # Heuristic: insufficient spec (gibberish / not enough detail) => reject
        critical = [spec.get("product_type"), spec.get("quantity"), spec.get("size")]
        missing_critical = sum(1 for v in critical if not v)
        if missing_critical >= 2:
            self._add_issue(issues, "insufficient_spec")

        # Resolution check: prefer numeric min_dpi if present
        min_dpi = spec.get("min_dpi")
        if min_dpi is not None:
            try:
                dpi_val = int(min_dpi)
                if dpi_val < 300:
                    self._add_issue(issues, "low_resolution")
            except Exception:
                self._add_issue(issues, "bad_dpi_value")

        # Size validation
        size = spec.get("size")
        if not size:
            self._add_issue(issues, "missing_size")
        else:
            if "x" in size:
                parts = size.split("x")
                try:
                    w = float(parts[0].replace("mm", ""))
                    h = float(parts[1].replace("mm", ""))
                    if w <= 0 or h <= 0:
                        self._add_issue(issues, "invalid_size")
                except Exception:
                    self._add_issue(issues, "invalid_size_format")
            else:
                self._add_issue(issues, "invalid_size_format")

        # Turnaround validation
        td = spec.get("turnaround_days")
        if td is None:
            self._add_issue(issues, "missing_turnaround")
        else:
            try:
                td_val = int(td)
                if td_val <= 0 or td_val > 365:
                    self._add_issue(issues, "invalid_turnaround")
            except Exception:
                self._add_issue(issues, "invalid_turnaround_format")

        # Finishing support
        finishing_list = spec.get("finishing", []) or []
        for f in finishing_list:
            if f not in SUPPORTED_FINISHING:
                self._add_issue(issues, f"unsupported_finishing:{f}")

        # If no finishing specified or finishing is 'none', require CSR review by default
        if not finishing_list or (len(finishing_list) == 1 and finishing_list[0] == "none"):
            self._add_issue(issues, "finishing_unconfirmed")

        # Turnaround urgent handling: very short turnarounds (1 day or less) require review
        td_val = None
        try:
            td_val = int(spec.get("turnaround_days") if spec.get("turnaround_days") is not None else -1)
        except Exception:
            td_val = None
        if td_val is not None and td_val <= 1:
            self._add_issue(issues, "urgent_turnaround")

        # Determine decision priority: rejected if any 'invalid_' or 'unsupported_finishing' present, or special rejections
        rejected_indicators = [i for i in issues if i.startswith("invalid_") or i.startswith("unsupported_finishing") or i in ("free_pricing", "insufficient_spec")]
        if rejected_indicators:
            decision = "rejected"
        elif issues:
            decision = "needs_review"
        else:
            decision = "auto_approved"

        # deterministic sort for reproducibility
        issues_sorted = sorted(issues)

        return {"decision": decision, "issues": issues_sorted}
