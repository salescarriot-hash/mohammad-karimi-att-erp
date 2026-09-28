from __future__ import annotations
from decimal import Decimal
from typing import Any
from app.pricing.engine import calculate


def _d(v: Any) -> Decimal:
    return Decimal(str(v or 0))


def build_scenarios(base: dict[str, Any], margins: list[float], exchange_rates: list[float] | None = None) -> dict[str, Any]:
    rates = exchange_rates or [float(base.get('exchange_rate', 1))]
    scenarios = []
    for rate in rates:
        for margin in margins:
            pp, landed, selling, final, increment = calculate(
                base['purchase_price'], rate,
                [base.get(k, 0) for k in (
                    'freight_cost','insurance_cost','customs_cost','clearance_cost',
                    'local_delivery_cost','financial_cost','other_cost')],
                base.get('margin_type', 'MARKUP'), margin,
                base.get('rounding_method', 'NONE'), base.get('rounding_value'))
            scenarios.append({
                'exchange_rate': rate,
                'margin_value': margin,
                'purchase_cost_in_target_currency': float(pp),
                'landed_cost': float(landed),
                'calculated_selling_price': float(selling),
                'final_selling_price': float(final),
                'rounding_value': float(increment) if increment is not None else None,
            })
    return {'scenarios': scenarios, 'scenario_count': len(scenarios)}
