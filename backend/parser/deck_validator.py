"""
deck_validator.py
Validates that an uploaded PDF is actually a pitch deck before analysis begins.
"""

import re
from dataclasses import dataclass
from typing import Optional
import pdfplumber


PITCH_DECK_KEYWORDS = [
    "problem", "solution", "market", "team", "traction", "revenue",
    "funding", "ask", "investors", "startup", "raise", "growth",
    "product", "customers", "vision", "runway", "burn", "tam", "sam",
    "som", "series", "seed", "pre-seed", "valuation", "pitch", "deck",
    "opportunity", "business model", "use of funds", "roadmap",
]

MIN_PAGES = 5
MAX_PAGES = 60
MIN_KEYWORDS_REQUIRED = 3
MAX_WORDS_PER_SLIDE = 300
TYPICAL_MAX_WORDS_PER_SLIDE = 150


@dataclass
class ValidationResult:
    is_valid: bool
    rejection_reason: Optional[str]
    page_count: int
    keyword_matches: list[str]
    avg_words_per_page: float
    confidence: float


def validate_pitch_deck(pdf_path: str) -> ValidationResult:
    """
    Validates that a PDF is a pitch deck.
    Returns a ValidationResult with is_valid flag and rejection details if invalid.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = pdf.pages
            page_count = len(pages)

            # Check page count
            if page_count < MIN_PAGES:
                return ValidationResult(
                    is_valid=False,
                    rejection_reason=f"This PDF has only {page_count} page(s). Pitch decks typically have {MIN_PAGES}–{MAX_PAGES} slides. Please upload a complete pitch deck.",
                    page_count=page_count,
                    keyword_matches=[],
                    avg_words_per_page=0.0,
                    confidence=0.0,
                )

            if page_count > MAX_PAGES:
                return ValidationResult(
                    is_valid=False,
                    rejection_reason=f"This PDF has {page_count} pages, which exceeds the maximum of {MAX_PAGES} for pitch decks. This appears to be a long-form document rather than a presentation.",
                    page_count=page_count,
                    keyword_matches=[],
                    avg_words_per_page=0.0,
                    confidence=0.0,
                )

            # Extract text and word counts per page
            all_text = ""
            word_counts = []
            for page in pages:
                text = page.extract_text() or ""
                words = text.split()
                word_counts.append(len(words))
                all_text += " " + text.lower()

            avg_words = sum(word_counts) / max(len(word_counts), 1)

            # Check word density — dense documents are likely reports, not decks
            if avg_words > MAX_WORDS_PER_SLIDE:
                return ValidationResult(
                    is_valid=False,
                    rejection_reason=f"This document averages {avg_words:.0f} words per page. Pitch decks are typically visual with 30–150 words per slide. This appears to be a report or long-form document.",
                    page_count=page_count,
                    keyword_matches=[],
                    avg_words_per_page=avg_words,
                    confidence=0.0,
                )

            # Keyword matching
            found_keywords = []
            for kw in PITCH_DECK_KEYWORDS:
                if re.search(r'\b' + re.escape(kw) + r'\b', all_text):
                    found_keywords.append(kw)

            if len(found_keywords) < MIN_KEYWORDS_REQUIRED:
                return ValidationResult(
                    is_valid=False,
                    rejection_reason=(
                        f"This PDF does not appear to be a pitch deck. Only {len(found_keywords)} pitch-deck keyword(s) were found "
                        f"({', '.join(found_keywords) if found_keywords else 'none'}). "
                        f"Expected at least {MIN_KEYWORDS_REQUIRED} of: problem, solution, market, team, traction, revenue, funding, etc."
                    ),
                    page_count=page_count,
                    keyword_matches=found_keywords,
                    avg_words_per_page=avg_words,
                    confidence=0.0,
                )

            # Compute confidence score
            keyword_score = min(len(found_keywords) / 8.0, 1.0)
            density_score = max(0.0, 1.0 - (avg_words / TYPICAL_MAX_WORDS_PER_SLIDE))
            page_score = 1.0 if MIN_PAGES <= page_count <= 30 else 0.6
            confidence = (keyword_score * 0.5 + density_score * 0.3 + page_score * 0.2) * 100

            return ValidationResult(
                is_valid=True,
                rejection_reason=None,
                page_count=page_count,
                keyword_matches=found_keywords,
                avg_words_per_page=avg_words,
                confidence=round(confidence, 1),
            )

    except Exception as e:
        return ValidationResult(
            is_valid=False,
            rejection_reason=f"Failed to read the PDF file: {str(e)}. Please ensure the file is a valid, non-encrypted PDF.",
            page_count=0,
            keyword_matches=[],
            avg_words_per_page=0.0,
            confidence=0.0,
        )
