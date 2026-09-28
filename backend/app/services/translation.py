from __future__ import annotations

import re
from typing import Any

PERSIAN_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")


GLOSSARY = {
    "شیر پروانه ای": "Butterfly Valve",
    "شیر پروانه‌ای": "Butterfly Valve",
    "شیر توپی": "Ball Valve",
    "شیر سوزنی": "Needle Valve",
    "شیر کنترل": "Control Valve",
    "شیر اطمینان": "Safety Valve",
    "شیر قطع و وصل": "On/Off Valve",
    "شیر یکطرفه": "Check Valve",
    "شیر یک طرفه": "Check Valve",

    "فیلتر هوا": "Air Filter",
    "فیلتر روغن": "Oil Filter",
    "فیلتر سوخت": "Fuel Filter",
    "فیلتر گاز": "Gas Filter",
    "المنت فیلتر": "Filter Element",
    "المنت": "Element",

    "واشر مسی": "Copper Washer",
    "واشر": "Washer",
    "گسکت": "Gasket",
    "اورینگ": "O-Ring",

    "پیچ": "Bolt / Screw",
    "مهره": "Nut",

    "یاتاقان": "Bearing",
    "بلبرینگ": "Ball Bearing",
    "رولبرینگ": "Roller Bearing",

    "پمپ": "Pump",
    "موتور": "Motor",
    "الکتروموتور": "Electric Motor",
    "ژنراتور": "Generator",
    "ترانسفورماتور": "Transformer",
    "ترانسمیتر": "Transmitter",
    "سنسور": "Sensor",

    "پرشر سوئیچ": "Pressure Switch",
    "سوئیچ فشار": "Pressure Switch",
    "سوئیچ": "Switch",
    "رله": "Relay",
    "کنتاکتور": "Contactor",

    "شمع": "Spark Plug",

    "نازل سوخت": "Fuel Nozzle",
    "نازل سوخت پاش": "Fuel Injection Nozzle",
    "نازل": "Nozzle",

    "روتور": "Rotor",
    "استاتور": "Stator",
    "پره توربین": "Turbine Blade",
    "پره کمپرسور": "Compressor Blade",
    "پره": "Blade",
    "کمپرسور": "Compressor",
    "توربین": "Turbine",

    "احتراق": "Combustion",
    "محفظه احتراق": "Combustion Chamber",
    "محفظه": "Chamber",

    "اکچویتور": "Actuator",
    "عملگر": "Actuator",

    "شفت": "Shaft",
    "محور": "Shaft",
    "کوپلینگ": "Coupling",
    "فلنج": "Flange",
    "لوله": "Pipe",
    "تیوب": "Tube",
    "شلنگ": "Hose",

    "کابل": "Cable",
    "سیم": "Wire",
    "برد": "Circuit Board",
    "ماژول": "Module",
    "کنترلر": "Controller",
    "کنترل": "Control",
    "کارت": "Card",

    "دستگاه": "Device",
    "تجهیزات": "Equipment",

    "قطعات یدکی": "Spare Parts",
    "قطعه یدکی": "Spare Part",
    "قطعه": "Part",

    "مشخصات فنی": "Technical Specifications",
    "مشخصات": "Specifications",
    "فنی": "Technical",

    "تعداد": "Quantity",
    "مقدار": "Quantity",
    "واحد": "Unit",

    "برند": "Brand",
    "سازنده": "Manufacturer",
    "مدل": "Model",

    "شماره فنی": "Part Number",
    "شماره قطعه": "Part Number",
    "شماره سریال": "Serial Number",
    "سریال": "Serial Number",
    "شماره تجهیز": "Equipment Number",

    "شرایط تحویل": "Delivery Requirement",
    "مدارک مورد نیاز": "Required Documents",
    "مدارک لازم": "Required Documents",

    "عدد": "EA / Piece",
    "ست": "Set",
    "مجموعه": "Set",
    "متر": "Meter",
    "کیلوگرم": "Kilogram",
    "لیتر": "Liter",

    "توربین های گازی": "Gas Turbines",
    "توربین‌های گازی": "Gas Turbines",

    "قطعات یدکی توربین های گازی": "Gas Turbine Spare Parts",
    "قطعات یدکی توربین‌های گازی": "Gas Turbine Spare Parts",

    "کراس فایر تیوب": "Crossfire Tube",
    "کراس فایر تیوب ها": "Crossfire Tubes",
    "کراس‌فایر تیوب": "Crossfire Tube",
    "کراس‌فایر تیوب‌ها": "Crossfire Tubes",

    "قطعات نازل سوخت": "Fuel Nozzle Components",

    "خرید": "Purchase",
    "تامین": "Supply",
    "تأمین": "Supply",
    "مناقصه": "Tender",
    "پیوست": "Attachment",
    "برنامه زمانبندی": "Schedule",
    "شماره": "Number",
}


def contains_persian(value: str | None) -> bool:
    return bool(value and PERSIAN_RE.search(value))


def normalize_persian(value: str) -> str:
    value = str(value or "")

    return (
        value
        .replace("\u064a", "\u06cc")
        .replace("\u0649", "\u06cc")
        .replace("\u0643", "\u06a9")
        .replace("\u200c", " ")
        .replace("\u200f", "")
        .replace("\u200e", "")
        .strip()
    )


def _apply_glossary(value: str) -> str:
    out = normalize_persian(value)

    for fa, en in sorted(
        GLOSSARY.items(),
        key=lambda x: len(x[0]),
        reverse=True
    ):
        out = out.replace(
            normalize_persian(fa),
            en
        )

    return out


def translate_candidate(
    value: str | None,
    *,
    field_name: str | None = None
) -> dict[str, Any]:

    if value is None:
        return {
            "original_value": None,
            "translated_value": None,
            "translation_status": "NOT_APPLICABLE",
            "translation_confidence": 1.0,
            "translation_source": None,
        }

    original = normalize_persian(str(value).strip())

    if not contains_persian(original):
        return {
            "original_value": original,
            "translated_value": original,
            "translation_status": "NOT_REQUIRED",
            "translation_confidence": 1.0,
            "translation_source": "ORIGINAL_ENGLISH_OR_LATIN",
        }

    candidate = _apply_glossary(original)

    if not contains_persian(candidate):
        return {
            "original_value": original,
            "translated_value": candidate,
            "translation_status": "GLOSSARY_TRANSLATION",
            "translation_confidence": 0.90,
            "translation_source": "ATT_INDUSTRIAL_GLOSSARY",
        }

    return {
        "original_value": original,
        "translated_value": None,
        "translation_status": "TRANSLATION_REQUIRED",
        "translation_confidence": 0.0,
        "translation_source": "PENDING_AI_TRANSLATION",
    }


def enrich_field(field: dict[str, Any]) -> dict[str, Any]:

    result = dict(field)

    translation = translate_candidate(
        result.get("value"),
        field_name=result.get("field_name")
    )

    result.update(translation)

    if (
        translation["translated_value"] is not None
        and result.get("field_name") == "description_original"
    ):
        result["normalized_value"] = translation["translated_value"]

    return result