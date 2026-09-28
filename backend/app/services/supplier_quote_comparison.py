from __future__ import annotations
from typing import Any
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.rfq import RFQ, RFQLine
from app.models.supplier import SupplierQuoteLine, SupplierQuote, Supplier
from app.services.commercial_intelligence import analyze_line


def _n(v):
    return str(v).strip().upper() if v is not None else None


def compare_quotes_for_line(db: Session, line_id: int) -> dict[str, Any]:
    line = db.get(RFQLine, line_id)
    if not line:
        raise ValueError("RFQ line not found")
    rfq = db.get(RFQ, line.rfq_id)
    stmt = (select(SupplierQuoteLine, SupplierQuote, Supplier)
            .join(SupplierQuote, SupplierQuote.id == SupplierQuoteLine.supplier_quote_id)
            .join(Supplier, Supplier.id == SupplierQuote.supplier_id)
            .where(SupplierQuoteLine.rfq_line_id == line_id))
    rows = []
    for ql, q, s in db.execute(stmt).all():
        price = float(ql.unit_price) if ql.unit_price is not None else None
        target = None
        market = analyze_line(db, line_id, currency=q.currency)
        if market.get("target_purchase_price") is not None and _n(market.get("target_currency")) == _n(q.currency):
            target = float(market["target_purchase_price"])
        delta = None
        delta_pct = None
        if price is not None and target and target > 0:
            delta = round(price - target, 6)
            delta_pct = round((price - target) / target * 100, 2)
        exact_pn = bool(line.customer_part_number and ql.supplier_part_number and _n(line.customer_part_number) == _n(ql.supplier_part_number))
        rows.append({
            "quote_line_id": ql.id, "quote_id": q.id, "supplier_id": s.id,
            "supplier_name": s.name, "quote_number": q.quote_number,
            "price": price, "currency": q.currency, "total_price": float(ql.total_price) if ql.total_price is not None else None,
            "supplier_part_number": ql.supplier_part_number, "exact_part_number": exact_pn,
            "manufacturer": ql.manufacturer, "brand": ql.brand, "condition": ql.condition,
            "availability": ql.availability, "lead_time": ql.lead_time, "technical_compliance": ql.technical_compliance,
            "incoterm": q.incoterm, "origin": q.origin, "warranty": q.warranty,
            "target_purchase_price": target, "price_delta_to_target": delta, "price_delta_percent": delta_pct,
            "deviation": ql.deviation, "quote_status": q.status,
            "selection_eligible": ql.technical_compliance not in ("NON_COMPLIANT", "PARTIALLY_COMPLIANT"),
        })
    currencies = sorted({_n(x["currency"]) for x in rows if x.get("currency")})
    return {
        "rfq_line": {"id": line.id, "rfq_id": line.rfq_id, "line_number": line.line_number,
                     "description": line.description_original or line.description_normalized,
                     "part_number": line.customer_part_number, "manufacturer": line.manufacturer,
                     "quantity": float(line.quantity) if line.quantity is not None else None,
                     "unit": line.unit, "condition": line.condition_required},
        "rfq": {"currency": rfq.currency if rfq else None, "incoterm": rfq.incoterm if rfq else None},
        "offers": rows,
        "currency_groups": currencies,
        "comparison_notes": [
            "Prices in different currencies are displayed separately and are not numerically compared.",
            "Exact P/N is shown separately from different supplier P/N; different P/N is not treated as an approved equivalent.",
            "Technical compliance and condition are displayed independently from price.",
            "Selection eligibility is a data-control flag, not an automatic supplier recommendation.",
        ],
        "requires_user_decision": bool(rows),
    }
