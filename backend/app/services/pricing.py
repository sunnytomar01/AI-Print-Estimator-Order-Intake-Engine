from typing import Dict, Any

class PriceEngine:
    """Rule-based pricing engine."""

    MATERIAL_COST = {
        "C300": 0.05,  # per unit
        "C350": 0.06,
        "standard": 0.04,
    }

    SETUP_COST = {
        "digital": 10.0,
        "offset": 50.0,
    }

    FINISHING_COST = {
        "lamination": 0.02,
        "spot_uv": 0.05,
        "die_cut": 0.10,
        "none": 0.0,
    }

    def _choose_process(self, quantity: int) -> str:
        return "digital" if quantity < 1000 else "offset"

    def estimate(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        qty = spec.get("quantity", 0)
        paper = spec.get("paper_type", "standard")
        finishing = spec.get("finishing", ["none"]) or ["none"]
        rush = spec.get("rush", False)
        turnaround = spec.get("turnaround_days", 0)

        process = self._choose_process(qty)
        material_unit = self.MATERIAL_COST.get(paper, self.MATERIAL_COST["standard"])
        material_cost = material_unit * qty

        setup = self.SETUP_COST[process]

        finishing_cost = sum(self.FINISHING_COST.get(f, 0.0) * qty for f in finishing)

        rush_surcharge = 0.2 if rush else 0.0

        base = material_cost + setup + finishing_cost
        margin = 0.2
        price = base * (1 + margin + rush_surcharge)

        return {
            "process": process,
            "material_unit": material_unit,
            "material_cost": material_cost,
            "setup_cost": setup,
            "finishing_cost": finishing_cost,
            "margin_pct": margin,
            "rush_surcharge_pct": rush_surcharge,
            "final_price": round(price, 2),
            "breakdown": {
                "base": base,
                "margin_amount": base * margin,
                "rush_amount": base * rush_surcharge,
            },
        }
