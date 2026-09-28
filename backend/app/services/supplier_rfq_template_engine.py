from __future__ import annotations
from copy import copy
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import re
from openpyxl import load_workbook
from openpyxl.formula.translate import Translator

TOKEN_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")


def _fmt(value):
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return f"{value:,.4f}".rstrip("0").rstrip(".")
    return str(value)


def _replace(value, mapping):
    if not isinstance(value, str):
        return value
    out = value
    for token, val in mapping.items():
        out = out.replace(token, _fmt(val))
    return out


def _style_row(ws, src_row, dst_row):
    for col in range(1, ws.max_column + 1):
        src = ws.cell(src_row, col)
        dst = ws.cell(dst_row, col)
        if src.has_style:
            dst._style = copy(src._style)
        if src.number_format:
            dst.number_format = src.number_format
        if src.alignment:
            dst.alignment = copy(src.alignment)
        if src.protection:
            dst.protection = copy(src.protection)
    if src_row in ws.row_dimensions:
        ws.row_dimensions[dst_row].height = ws.row_dimensions[src_row].height


def _copy_row_formulas(ws, src_row, dst_row):
    for col in range(1, ws.max_column + 1):
        value = ws.cell(src_row, col).value
        if isinstance(value, str) and value.startswith("="):
            try:
                ws.cell(dst_row, col).value = Translator(value, origin=ws.cell(src_row, col).coordinate).translate_formula(ws.cell(dst_row, col).coordinate)
            except Exception:
                ws.cell(dst_row, col).value = value


def inspect_supplier_rfq_template(path: Path):
    wb = load_workbook(path, data_only=False)
    tokens = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    tokens.extend(TOKEN_RE.findall(cell.value))
    unique = []
    for token in tokens:
        if token not in unique:
            unique.append(token)
    return {
        "sheets": wb.sheetnames,
        "tokens": unique,
        "line_tokens": [x for x in unique if x.startswith("line.")],
    }


def _line_mapping(line, index):
    return {
        "{{line.number}}": getattr(line, "line_number", index),
        "{{line.description}}": getattr(line, "description_normalized", None) or getattr(line, "description_original", None),
        "{{line.manufacturer}}": getattr(line, "manufacturer", None),
        "{{line.part_number}}": getattr(line, "customer_part_number", None),
        "{{line.quantity}}": getattr(line, "quantity", None),
        "{{line.unit}}": getattr(line, "unit", None),
        "{{line.condition}}": getattr(line, "condition_required", None),
        "{{line.technical_requirements}}": getattr(line, "technical_requirements", None),
        "{{line.documents_required}}": getattr(line, "documents_required", None),
        "{{line.delivery_requirement}}": getattr(line, "delivery_requirement", None),
    }


def render_supplier_rfq(template_path: Path, output_path: Path, rfq, supplier, lines):
    wb = load_workbook(template_path)
    header = {
        "{{rfq.number}}": getattr(rfq, "customer_rfq_number", None),
        "{{rfq.title}}": getattr(rfq, "title", None),
        "{{rfq.date}}": getattr(rfq, "request_date", None),
        "{{rfq.required_date}}": getattr(rfq, "required_date", None),
        "{{rfq.currency}}": getattr(rfq, "currency", None),
        "{{rfq.delivery_location}}": getattr(rfq, "delivery_location", None),
        "{{rfq.incoterm}}": getattr(rfq, "incoterm", None),
        "{{supplier.name}}": getattr(supplier, "name", None),
        "{{supplier.name_en}}": getattr(supplier, "name_en", None),
        "{{supplier.country}}": getattr(supplier, "country", None),
        "{{supplier.city}}": getattr(supplier, "city", None),
        "{{supplier.contact_name}}": getattr(supplier, "contact_name", None),
        "{{supplier.email}}": getattr(supplier, "email", None),
        "{{supplier.phone}}": getattr(supplier, "phone", None),
    }
    for ws in wb.worksheets:
        marker_rows = []
        for row in range(1, ws.max_row + 1):
            values = [ws.cell(row, c).value for c in range(1, ws.max_column + 1)]
            if any(isinstance(v, str) and "{{line." in v for v in values):
                marker_rows.append(row)
        if marker_rows:
            marker = marker_rows[0]
            template_values = [ws.cell(marker, c).value for c in range(1, ws.max_column + 1)]
            # Preserve merged cells by only expanding the row content; official templates can use a dedicated line row.
            if not lines:
                ws.delete_rows(marker, 1)
            else:
                for idx, line in enumerate(lines):
                    target = marker + idx
                    if idx > 0:
                        ws.insert_rows(target, 1)
                        _style_row(ws, marker, target)
                        _copy_row_formulas(ws, marker, target)
                    mapping = {**header, **_line_mapping(line, idx + 1)}
                    for col, original in enumerate(template_values, 1):
                        if isinstance(original, str):
                            ws.cell(target, col).value = _replace(original, mapping)
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    cell.value = _replace(cell.value, header)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path
