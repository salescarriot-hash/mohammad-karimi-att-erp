from typing import Protocol

class RFQExtractor(Protocol):
    def extract(self, filename: str, text: str) -> dict:
        """Return candidate fields/lines with confidence and source; never write to DB."""
        ...

class RuleBasedRFQExtractor:
    """V1 deterministic fallback. Replace/augment with an LLM/OCR adapter later."""
    def extract(self, filename: str, text: str) -> dict:
        from app.services.rfq_intake import build_preview_from_text
        return build_preview_from_text(filename, text)
