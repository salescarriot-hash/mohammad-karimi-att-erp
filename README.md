# ARTIN TOURBINE TECHNOLOGY (ATT) ERP

Initial implementation package.

- `ATT-ERP-db/001_initial_schema.sql` — PostgreSQL Migration 001
- `ATT-ERP-db/ATT_ERP_ERD.mmd` — ERD
- `backend/` — FastAPI backend starter
- `storage/` — initial local file-storage structure
- `config/` — application configuration area

## Current implementation status
- Customer, Case, File, RFQ and RFQ Line CRUD APIs are implemented.
- RFQ Intake baseline extraction supports PDF text, XLSX/XLSM, DOCX, CSV/TXT.
- Intake returns candidate values with confidence and source; it does not silently make them authoritative.
- Verification Center API supports PENDING / CONFIRMED / EDITED / REJECTED / NEEDS_CLARIFICATION.
- Uploaded Case files can be re-processed for RFQ intake.
- RFQ draft creation from a Case file is explicitly marked UNDER_REVIEW; extracted lines remain PENDING.
- AI extraction remains an adapter boundary; the current fallback is rule-based and deterministic.

## RFQ Intake — Extraction → Translation → Verification

The RFQ intake pipeline now has an explicit translation stage after document text extraction and before RFQ/master-data mapping:

`File → Text/Structure Extraction → Persian/English Detection → English Translation Candidate → Verification → RFQ/ERP`

Rules:
- The customer's original Persian text is always preserved.
- English translations are stored as candidates and carry translation status/confidence/source.
- Common industrial terms and units are translated by the ATT industrial glossary.
- Text not covered safely by the local glossary is marked `TRANSLATION_REQUIRED`; the system does not invent an English value.
- Translation candidates generate `TRANSLATION_REVIEW` Verification Tasks before they can become authoritative ERP data.
- Part descriptions use the English candidate as `description_normalized`; `description_original` remains the customer's original wording.
- A document that yields no reliable RFQ fields/lines cannot create an empty RFQ draft; intake stops with a clear validation error.
- Persian RFQ headers are recognized directly, including description, manufacturer, part number, quantity, unit, technical specification, documents and delivery fields.
