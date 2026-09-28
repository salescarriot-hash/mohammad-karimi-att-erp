from difflib import SequenceMatcher


def norm(v):
    if v is None:
        return ""
    return "".join(ch.lower() for ch in str(v).strip() if ch.isalnum())


def text_similarity(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    return round(SequenceMatcher(None, a, b).ratio(), 4)


def compare_quote_line(rfq_line, quote_line, quote_currency=None):
    conflicts = []

    def add(field, severity, expected, actual, reason):
        conflicts.append({
            "field": field, "severity": severity, "expected": expected,
            "actual": actual, "reason": reason,
        })

    if rfq_line.quantity is not None and quote_line.quantity is not None:
        if float(rfq_line.quantity) != float(quote_line.quantity):
            add("quantity", "HIGH", str(rfq_line.quantity), str(quote_line.quantity), "Supplier quoted a different quantity.")

    if rfq_line.unit and quote_line.unit and norm(rfq_line.unit) != norm(quote_line.unit):
        add("unit", "HIGH", rfq_line.unit, quote_line.unit, "Supplier quoted a different unit of measure.")

    required_condition = (rfq_line.condition_required or "").upper()
    supplier_condition = (quote_line.condition or "").upper()
    if required_condition and required_condition not in {"ANY", "OTHER"} and supplier_condition and supplier_condition != required_condition:
        add("condition", "HIGH", rfq_line.condition_required, quote_line.condition, "Supplier condition differs from customer requirement.")

    if rfq_line.manufacturer and quote_line.manufacturer:
        if norm(rfq_line.manufacturer) != norm(quote_line.manufacturer):
            add("manufacturer", "MEDIUM", rfq_line.manufacturer, quote_line.manufacturer, "Manufacturer differs; review OEM/equivalent status.")

    if rfq_line.customer_part_number and quote_line.supplier_part_number:
        if norm(rfq_line.customer_part_number) != norm(quote_line.supplier_part_number):
            add("part_number", "MEDIUM", rfq_line.customer_part_number, quote_line.supplier_part_number, "Supplier P/N differs; this is a deviation, not an automatic conflict because it may be an equivalent/alternate.")

    if rfq_line.delivery_requirement and quote_line.lead_time:
        # Only flag a delivery deviation when the textual requirements differ.
        # We deliberately avoid guessing date/lead-time semantics.
        if norm(rfq_line.delivery_requirement) != norm(quote_line.lead_time):
            add("delivery", "MEDIUM", rfq_line.delivery_requirement, quote_line.lead_time, "Supplier lead time differs from the stated delivery requirement; user review is required.")

    description_score = text_similarity(rfq_line.description_normalized or rfq_line.description_original, quote_line.description)
    if quote_line.description and description_score < 0.45:
        add("description", "MEDIUM", rfq_line.description_original, quote_line.description, f"Low description similarity ({description_score}).")

    return conflicts, description_score


def compare_quote(rfq, rfq_lines, quote, quote_lines):
    line_map = {line.rfq_line_id: line for line in quote_lines}
    results = []
    unmatched = []
    for rl in rfq_lines:
        ql = line_map.get(rl.id)
        if not ql:
            unmatched.append({"rfq_line_id": rl.id, "line_number": rl.line_number, "reason": "No supplier quote line linked."})
            continue
        conflicts, similarity = compare_quote_line(rl, ql, quote.currency)
        results.append({
            "rfq_line_id": rl.id, "supplier_quote_line_id": ql.id,
            "line_number": rl.line_number, "description_similarity": similarity,
            "conflicts": conflicts,
            "conflict_count": len(conflicts),
            "technical_compliance": ql.technical_compliance,
        })

    quote_line_ids = {x.rfq_line_id for x in quote_lines}
    extra = [
        {"supplier_quote_line_id": q.id, "rfq_line_id": q.rfq_line_id, "reason": "Supplier quote line is linked to an RFQ line outside the expected set."}
        for q in quote_lines if q.rfq_line_id not in {r.id for r in rfq_lines}
    ]

    header_conflicts = []
    if rfq.currency and quote.currency and norm(rfq.currency) != norm(quote.currency):
        header_conflicts.append({"field": "currency", "severity": "HIGH", "expected": rfq.currency, "actual": quote.currency, "reason": "Supplier quote currency differs from RFQ currency."})
    if rfq.incoterm and quote.incoterm and norm(rfq.incoterm) != norm(quote.incoterm):
        header_conflicts.append({"field": "incoterm", "severity": "MEDIUM", "expected": rfq.incoterm, "actual": quote.incoterm, "reason": "Supplier quote Incoterm differs from RFQ Incoterm."})

    return {
        "rfq_id": rfq.id,
        "supplier_quote_id": quote.id,
        "header_conflicts": header_conflicts,
        "line_results": results,
        "unmatched_rfq_lines": unmatched,
        "extra_supplier_lines": extra,
        "requires_user_confirmation": bool(header_conflicts or unmatched or extra or any(x["conflict_count"] for x in results)),
    }
