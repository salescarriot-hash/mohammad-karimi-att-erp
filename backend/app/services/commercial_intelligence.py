from __future__ import annotations

from datetime import date
from statistics import median
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.commercial import MarketPrice
from app.models.master import Part
from app.models.rfq import RFQLine
from app.models.supplier import SupplierQuote, SupplierQuoteLine


def _norm(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip().upper()
    return s or None


def _same(a: Any, b: Any) -> bool:
    aa, bb = _norm(a), _norm(b)
    return aa is not None and bb is not None and aa == bb


def _days_old(observed: date | None) -> int | None:
    if not observed:
        return None
    return max((date.today() - observed).days, 0)


def _iqr_bounds(values: list[float]) -> tuple[float | None, float | None]:
    if len(values) < 4:
        return None, None
    xs = sorted(values)
    mid = len(xs) // 2
    lower = xs[:mid]
    upper = xs[mid:] if len(xs) % 2 == 0 else xs[mid + 1 :]
    q1 = median(lower)
    q3 = median(upper)
    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def _source_confidence(value: str | None) -> float:
    return {"HIGH": 1.0, "MEDIUM": 0.75, "LOW": 0.5, "INSUFFICIENT_DATA": 0.2}.get(_norm(value) or "", 0.5)


def _observation_score(o: dict[str, Any], target_pn: str | None, target_brand: str | None,
                       target_condition: str | None) -> float:
    score = 0.0
    if target_pn and _same(o.get("part_number"), target_pn):
        score += 0.40
    elif target_pn and _same(o.get("supplier_part_number"), target_pn):
        score += 0.40
    if target_brand and (_same(o.get("brand"), target_brand) or _same(o.get("manufacturer"), target_brand)):
        score += 0.20
    if target_condition and target_condition != "ANY" and _same(o.get("condition"), target_condition):
        score += 0.20
    score += 0.10 * _source_confidence(o.get("confidence"))
    age = o.get("age_days")
    if age is not None:
        score += 0.10 * max(0.0, 1.0 - min(age, 365) / 365.0)
    return round(min(score, 1.0), 4)


def analyze_line(db: Session, line_id: int, currency: str | None = None,
                 include_equivalents: bool = False) -> dict[str, Any]:
    line = db.get(RFQLine, line_id)
    if not line:
        raise ValueError("RFQ line not found")

    part = db.get(Part, line.part_id) if line.part_id else None
    target_pn = (part.part_number if part else None) or line.customer_part_number
    target_brand = (part.manufacturer.name if getattr(part, "manufacturer", None) else None) if part else line.manufacturer
    target_brand = target_brand or line.manufacturer
    target_condition = _norm(line.condition_required) or "NEW"
    requested_currency = _norm(currency)

    observations: list[dict[str, Any]] = []

    qstmt = (
        select(SupplierQuoteLine, SupplierQuote)
        .join(SupplierQuote, SupplierQuote.id == SupplierQuoteLine.supplier_quote_id)
        .where(SupplierQuoteLine.rfq_line_id == line_id)
    )
    for ql, q in db.execute(qstmt).all():
        if ql.unit_price is None or not q.currency:
            continue
        if requested_currency and _norm(q.currency) != requested_currency:
            continue
        if ql.technical_compliance in ("NON_COMPLIANT", "PARTIALLY_COMPLIANT"):
            continue
        qcond = _norm(ql.condition)
        if target_condition != "ANY" and qcond and qcond != target_condition:
            continue
        exact = bool(target_pn and _same(ql.supplier_part_number, target_pn))
        # A different supplier P/N is not silently considered equivalent. It is only
        # eligible in the expanded set when the quote line is technically reviewed.
        if target_pn and ql.supplier_part_number and not exact and not include_equivalents:
            continue
        observations.append({
            "source": "SUPPLIER_QUOTE",
            "source_id": ql.id,
            "supplier_quote_id": q.id,
            "supplier_id": q.supplier_id,
            "supplier_part_number": ql.supplier_part_number,
            "part_number": target_pn if exact else ql.supplier_part_number,
            "price": float(ql.unit_price),
            "currency": q.currency,
            "condition": ql.condition,
            "brand": ql.brand,
            "manufacturer": ql.manufacturer,
            "availability": ql.availability,
            "lead_time": ql.lead_time,
            "confidence": "HIGH" if q.status in ("RECEIVED", "ACCEPTED") else "MEDIUM",
            "exact_part_number": exact,
            "age_days": _days_old(q.quote_date),
        })

    mstmt = select(MarketPrice)
    if part:
        mstmt = mstmt.where(MarketPrice.part_id == part.id)
    elif target_pn:
        mstmt = mstmt.where(MarketPrice.part_number.ilike(target_pn))
    for m in db.scalars(mstmt).all():
        if m.unit_price is None or not m.currency or m.verification_status == "REJECTED":
            continue
        if requested_currency and _norm(m.currency) != requested_currency:
            continue
        if target_condition != "ANY" and m.condition and _norm(m.condition) != target_condition:
            continue
        exact = bool(target_pn and _same(m.part_number, target_pn))
        observations.append({
            "source": "MARKET_PRICE",
            "source_id": m.id,
            "supplier_quote_id": None,
            "supplier_id": m.supplier_id,
            "supplier_part_number": None,
            "part_number": m.part_number,
            "price": float(m.unit_price),
            "currency": m.currency,
            "condition": m.condition,
            "brand": m.brand,
            "manufacturer": None,
            "availability": m.availability,
            "lead_time": m.lead_time,
            "confidence": m.confidence,
            "exact_part_number": exact,
            "age_days": _days_old(m.observed_date),
        })

    for o in observations:
        o["comparability_score"] = _observation_score(o, target_pn, target_brand, target_condition)
        o["classification"] = "EXACT" if o["exact_part_number"] else "EQUIVALENT_OR_ALTERNATE_CANDIDATE"

    exact = [o for o in observations if o["exact_part_number"]]
    expanded = observations if include_equivalents else exact
    values = [o["price"] for o in expanded]
    low, high = _iqr_bounds(values)
    filtered = [o for o in expanded if low is None or low <= o["price"] <= high]
    outliers = [o for o in expanded if o not in filtered]

    by_currency: dict[str, list[float]] = {}
    for o in filtered:
        by_currency.setdefault(_norm(o["currency"]) or "UNKNOWN", []).append(o["price"])
    summaries = []
    for cur, vals in by_currency.items():
        summaries.append({
            "currency": cur,
            "count": len(vals),
            "min": min(vals),
            "median": median(vals),
            "max": max(vals),
            "range_percent": round(((max(vals) - min(vals)) / median(vals) * 100), 2) if median(vals) else None,
        })

    target_currency = requested_currency
    if not target_currency and len(by_currency) == 1:
        target_currency = next(iter(by_currency))
    eligible = [o for o in filtered if target_currency and _norm(o["currency"]) == target_currency]
    target = median([o["price"] for o in eligible]) if eligible else None
    data_confidence = "HIGH" if len(eligible) >= 3 else "MEDIUM" if len(eligible) >= 2 else "LOW" if len(eligible) == 1 else "INSUFFICIENT_DATA"

    warning = None
    if not eligible:
        warning = "No comparable observations in the requested currency and condition."
    elif len(eligible) < 2:
        warning = "Only one comparable observation is available; treat Target Purchase Price as low-confidence."
    elif outliers:
        warning = f"{len(outliers)} statistical outlier(s) excluded using IQR; historical observations remain preserved."
    if not exact and include_equivalents:
        warning = (warning + " " if warning else "") + "Expanded set includes non-exact P/N observations; technical equivalence must be user-confirmed."

    return {
        "rfq_line_id": line_id,
        "part_id": line.part_id,
        "part_number": target_pn,
        "target_brand": target_brand,
        "requested_condition": target_condition,
        "requested_currency": target_currency,
        "include_equivalents": include_equivalents,
        "observations": observations,
        "eligible_observations": eligible,
        "outliers": outliers,
        "summaries": summaries,
        "target_purchase_price": target,
        "target_currency": target_currency,
        "method": "MEDIAN_EXACT_COMPARABLES_WITH_IQR_FILTER",
        "data_confidence": data_confidence,
        "comparable_count": len(eligible),
        "warning": warning,
        "notes": [
            "Target Purchase Price is an analytical estimate, not a market fact.",
            "OEM/exact P/N observations are separated from equivalent/alternate candidates.",
            "Historical observations are preserved; filtering only affects this analysis snapshot.",
        ],
    }
