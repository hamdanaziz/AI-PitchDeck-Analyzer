'''
"""
pdf_parser.py
Layout-aware PDF extraction using pdfplumber and PyPDF2.
Extracts text, numbers, tables, and assigns slides to pitch deck categories.
"""

import re
from dataclasses import dataclass, field
from typing import Optional
import pdfplumber


# ---------------------------------------------------------------------------
# Category keyword weights
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS: dict[str, list[tuple[str, float]]] = {
    "Problem": [
        ("problem", 3.0), ("pain", 2.5), ("challenge", 2.0), ("issue", 1.5),
        ("gap", 1.5), ("struggle", 1.5), ("friction", 1.5), ("inefficiency", 1.5),
        ("broken", 1.5), ("cost of", 1.0), ("currently", 0.5),
    ],
    "Solution": [
        ("solution", 3.0), ("platform", 2.0), ("product", 2.0), ("how it works", 2.5),
        ("we built", 2.0), ("our approach", 2.0), ("technology", 1.5),
        ("ai", 1.0), ("software", 1.0), ("automate", 1.5), ("feature", 1.5),
    ],
    "Market Size": [
        ("tam", 3.0), ("sam", 3.0), ("som", 3.0), ("total addressable market", 3.0),
        ("market size", 3.0), ("billion", 1.5), ("trillion", 1.5),
        ("market opportunity", 2.0), ("industry", 1.5), ("segment", 1.0),
    ],
    "Business Model": [
        ("business model", 3.0), ("revenue model", 3.0), ("monetize", 2.5),
        ("subscription", 2.0), ("saas", 2.0), ("pricing", 2.0), ("unit economics", 2.5),
        ("ltv", 2.0), ("cac", 2.0), ("arpu", 2.0), ("per user", 1.5), ("fee", 1.0),
    ],
    "Traction": [
        ("traction", 3.0), ("customers", 2.0), ("users", 2.0), ("revenue", 2.0),
        ("growth", 2.0), ("mrr", 2.5), ("arr", 2.5), ("pilot", 2.0),
        ("partnership", 1.5), ("waitlist", 1.5), ("signed", 1.5), ("retention", 1.5),
    ],
    "Team": [
        ("team", 3.0), ("founder", 3.0), ("co-founder", 3.0), ("ceo", 2.0),
        ("cto", 2.0), ("advisor", 1.5), ("experience", 1.5), ("previously", 1.5),
        ("background", 1.5), ("phd", 1.0), ("ex-", 1.0), ("years at", 1.0),
    ],
    "Financials": [
        ("financials", 3.0), ("projection", 2.5), ("forecast", 2.5), ("burn", 2.5),
        ("runway", 2.5), ("revenue projection", 3.0), ("ebitda", 2.0),
        ("cash flow", 2.0), ("profit", 1.5), ("margin", 1.5), ("cogs", 2.0),
    ],
    "Ask": [
        ("raising", 3.0), ("raise", 2.5), ("ask", 2.5), ("use of funds", 3.0),
        ("investment", 2.0), ("seed", 1.5), ("series a", 2.0), ("pre-seed", 2.0),
        ("valuation", 2.5), ("equity", 2.0), ("close", 1.5), ("round", 1.5),
    ],
}

# Regex patterns for numeric extraction
PATTERNS = {
    "dollar_amounts": r"\$[\d,]+(?:\.\d+)?(?:\s*[kmb](?:illion|illion)?)?",
    "percentages": r"\d+(?:\.\d+)?\s*%",
    "multipliers": r"\d+(?:\.\d+)?[xX]",
    "years": r"20\d{2}",
    "large_numbers": r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b",
    "plain_numbers": r"\b\d+(?:\.\d+)?\b",
}


@dataclass
class SlideData:
    slide_number: int
    raw_text: str
    word_count: int
    numeric_values: dict[str, list[str]]
    tables: list[list[list[str]]]
    primary_category: str
    secondary_category: Optional[str]
    category_scores: dict[str, float]
    heading_hints: list[str]   # Large-font or short lines likely to be headings


@dataclass
class ParsedDeck:
    slides: list[SlideData]
    total_slides: int
    all_text: str
    all_numbers: list[str]
    category_slide_map: dict[str, list[int]]   # category -> list of slide numbers


def _extract_numeric_values(text: str) -> dict[str, list[str]]:
    results: dict[str, list[str]] = {}
    for key, pattern in PATTERNS.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            results[key] = [m.strip() for m in matches]
    return results


def _score_categories(text: str) -> dict[str, float]:
    text_lower = text.lower()
    scores: dict[str, float] = {}
    for category, kw_list in CATEGORY_KEYWORDS.items():
        score = 0.0
        for kw, weight in kw_list:
            if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                score += weight
        scores[category] = score
    return scores


def _extract_heading_hints(page) -> list[str]:
    """
    Heuristically identify heading-level text by looking at short lines
    or lines that appear to use larger fonts via character bbox height.
    """
    headings = []
    try:
        words = page.extract_words(extra_attrs=["size"])
        if not words:
            return headings
        all_sizes = [w.get("size", 12) for w in words]
        avg_size = sum(all_sizes) / max(len(all_sizes), 1)
        # Group words into lines by top position
        lines: dict[int, list] = {}
        for w in words:
            top_key = round(w.get("top", 0) / 5) * 5
            lines.setdefault(top_key, []).append(w)
        for top_key in sorted(lines.keys()):
            line_words = lines[top_key]
            line_text = " ".join(w["text"] for w in line_words)
            line_size = sum(w.get("size", 12) for w in line_words) / len(line_words)
            word_count = len(line_words)
            if line_size > avg_size * 1.3 and word_count <= 12 and len(line_text.strip()) > 4 and len(line_text.strip().replace(' ', '')) > 6:
                headings.append(line_text.strip())
    except Exception:
        pass
    return headings[:5]  # Cap at 5 headings per slide


def _extract_tables(page) -> list[list[list[str]]]:
    tables = []
    try:
        raw_tables = page.extract_tables()
        if raw_tables:
            for tbl in raw_tables:
                cleaned = [
                    [str(cell).strip() if cell else "" for cell in row]
                    for row in tbl
                ]
                tables.append(cleaned)
    except Exception:
        pass
    return tables


def parse_pdf(pdf_path: str) -> ParsedDeck:
    slides: list[SlideData] = []
    all_text_parts: list[str] = []
    all_numbers: list[str] = []

    import fitz  # PyMuPDF

    fitz_doc = fitz.open(pdf_path)

    with pdfplumber.open(pdf_path) as pdf:
        for idx, page in enumerate(pdf.pages):
            slide_num = idx + 1
            raw_text = page.extract_text() or ""

            # If pdfplumber got less than 30 chars, fall back to PyMuPDF
            if len(raw_text.strip()) < 30:
                try:
                    fitz_page = fitz_doc[idx]
                    raw_text = fitz_page.get_text("text") or ""
                except Exception:
                    pass
            all_text_parts.append(raw_text)

            word_count = len(raw_text.split())
            numeric_values = _extract_numeric_values(raw_text)
            tables = _extract_tables(page)
            heading_hints = _extract_heading_hints(page)
            category_scores = _score_categories(raw_text)

            # Collect all numeric values for global set
            for vals in numeric_values.values():
                all_numbers.extend(vals)

            # Sort categories by score descending
            sorted_cats = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
            primary = sorted_cats[0][0] if sorted_cats[0][1] > 0 else "Unknown"
            secondary = sorted_cats[1][0] if len(sorted_cats) > 1 and sorted_cats[1][1] > 0 else None

            slides.append(SlideData(
                slide_number=slide_num,
                raw_text=raw_text,
                word_count=word_count,
                numeric_values=numeric_values,
                tables=tables,
                primary_category=primary,
                secondary_category=secondary,
                category_scores=category_scores,
                heading_hints=heading_hints,
            ))

    # Build category -> slide map
    category_slide_map: dict[str, list[int]] = {}
    for slide in slides:
        cat = slide.primary_category
        category_slide_map.setdefault(cat, []).append(slide.slide_number)

    fitz_doc.close()

    return ParsedDeck(
        slides=slides,
        total_slides=len(slides),
        all_text=" ".join(all_text_parts),
        all_numbers=list(set(all_numbers)),
        category_slide_map=category_slide_map,
    )
'''

"""
pdf_parser.py
Layout-aware PDF extraction with Cohere semantic category classification.
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional
import pdfplumber
import cohere

# ---------------------------------------------------------------------------
# Cohere client (singleton)
# ---------------------------------------------------------------------------

_cohere_client = None

def _get_cohere():
    global _cohere_client
    if _cohere_client is None:
        _cohere_client = cohere.Client(os.environ.get("COHERE_API_KEY"))
    return _cohere_client


# ---------------------------------------------------------------------------
# Category reference sentences for semantic matching
# These describe what each section MEANS, not just keywords
# ---------------------------------------------------------------------------

CATEGORY_DESCRIPTIONS = {
    "Problem": [
        "This slide describes a problem, pain point, or challenge that customers face",
        "The founder explains what is broken, inefficient, or frustrating in the market today",
        "This slide shows why the current situation is bad and needs to change",
        "Customers are struggling with this issue and losing time or money because of it",
    ],
    "Solution": [
        "This slide describes the product or service being built to solve the problem",
        "The founder explains how their technology or platform works",
        "This slide shows what makes the solution unique or better than alternatives",
        "The product features and capabilities are described here",
    ],
    "Market Size": [
        "This slide shows how large the market opportunity is in dollar terms",
        "The total addressable market, serviceable market, and target segment are defined",
        "We are targeting a billion dollar industry or market opportunity",
        "The market size is estimated using bottom-up or top-down analysis",
    ],
    "Business Model": [
        "This slide explains how the company makes money",
        "The revenue model, pricing, and monetization strategy are described here",
        "We charge a subscription fee, commission, or transaction fee to generate revenue",
        "Unit economics including customer acquisition cost and lifetime value are shown",
    ],
    "Traction": [
        "This slide shows evidence that customers want and use the product",
        "Revenue, user growth, and key metrics demonstrate product market fit",
        "The company has signed customers, partnerships, or achieved significant milestones",
        "Growth numbers, retention data, and engagement metrics are presented here",
    ],
    "Team": [
        "This slide introduces the founders and key team members",
        "The backgrounds, experience, and domain expertise of the leadership team are shown",
        "The team previously worked at notable companies or has relevant credentials",
        "Advisors and board members supporting the company are mentioned here",
    ],
    "Financials": [
        "This slide shows revenue projections, financial forecasts, and future growth plans",
        "Burn rate, runway, and cash flow information is presented here",
        "The path to profitability and financial milestones are described",
        "Gross margins, operating expenses, and financial model assumptions are shown",
    ],
    "Ask": [
        "This slide states how much funding the company is raising and at what valuation",
        "The use of funds breakdown shows where investor money will be allocated",
        "The company is seeking investment to reach the next milestone",
        "The funding round size, terms, and strategic goals of the raise are described",
    ],
}

# Flatten to list of (text, category) for embedding
_CATEGORY_TEXTS = []
_CATEGORY_LABELS = []
for cat, descs in CATEGORY_DESCRIPTIONS.items():
    for desc in descs:
        _CATEGORY_TEXTS.append(desc)
        _CATEGORY_LABELS.append(cat)

# Cache for reference embeddings
_REFERENCE_EMBEDDINGS = None


def _get_reference_embeddings():
    global _REFERENCE_EMBEDDINGS
    if _REFERENCE_EMBEDDINGS is None:
        co = _get_cohere()
        response = co.embed(
            texts=_CATEGORY_TEXTS,
            model="embed-english-v3.0",
            input_type="search_document",
        )
        _REFERENCE_EMBEDDINGS = response.embeddings
    return _REFERENCE_EMBEDDINGS


def _cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x ** 2 for x in a) ** 0.5
    norm_b = sum(x ** 2 for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _score_categories_semantic(text: str) -> dict[str, float]:
    """
    Use Cohere embeddings to score how well a slide matches each category.
    Returns scores 0-10 per category based on semantic similarity.
    """
    if not text or len(text.strip()) < 10:
        return {cat: 0.0 for cat in CATEGORY_DESCRIPTIONS}

    try:
        co = _get_cohere()
        ref_embeddings = _get_reference_embeddings()

        # Embed the slide text
        response = co.embed(
            texts=[text[:2000]],  # cap to avoid token limits
            model="embed-english-v3.0",
            input_type="search_query",
        )
        slide_embedding = response.embeddings[0]

        # Compute similarity to each reference sentence
        category_scores: dict[str, list[float]] = {cat: [] for cat in CATEGORY_DESCRIPTIONS}
        for ref_emb, label in zip(ref_embeddings, _CATEGORY_LABELS):
            sim = _cosine_similarity(slide_embedding, ref_emb)
            category_scores[label].append(sim)

        # Take max similarity per category and scale to 0-10
        final_scores = {}
        for cat, sims in category_scores.items():
            max_sim = max(sims) if sims else 0.0
            # Cosine similarity ranges ~0.3-0.9 for relevant matches
            # Normalize: below 0.35 = 0, above 0.75 = 10
            normalized = max(0.0, (max_sim - 0.28) / 0.40) * 10
            final_scores[cat] = round(min(normalized, 10.0), 2)

        return final_scores

    except Exception:
        # Fall back to zero scores if Cohere fails
        return {cat: 0.0 for cat in CATEGORY_DESCRIPTIONS}


# ---------------------------------------------------------------------------
# Regex patterns for numeric extraction (unchanged)
# ---------------------------------------------------------------------------

PATTERNS = {
    "dollar_amounts": r"\$[\d,]+(?:\.\d+)?(?:\s*[kmb](?:illion)?)?",
    "percentages": r"\d+(?:\.\d+)?\s*%",
    "multipliers": r"\d+(?:\.\d+)?[xX]",
    "years": r"20\d{2}",
    "large_numbers": r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b",
    "plain_numbers": r"\b\d+(?:\.\d+)?\b",
}


@dataclass
class SlideData:
    slide_number: int
    raw_text: str
    word_count: int
    numeric_values: dict[str, list[str]]
    tables: list[list[list[str]]]
    primary_category: str
    secondary_category: Optional[str]
    category_scores: dict[str, float]
    heading_hints: list[str]


@dataclass
class ParsedDeck:
    slides: list[SlideData]
    total_slides: int
    all_text: str
    all_numbers: list[str]
    category_slide_map: dict[str, list[int]]


def _extract_numeric_values(text: str) -> dict[str, list[str]]:
    results: dict[str, list[str]] = {}
    for key, pattern in PATTERNS.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            results[key] = [m.strip() for m in matches]
    return results


def _extract_heading_hints(page) -> list[str]:
    headings = []
    try:
        words = page.extract_words(extra_attrs=["size"])
        if not words:
            return headings
        all_sizes = [w.get("size", 12) for w in words]
        avg_size = sum(all_sizes) / max(len(all_sizes), 1)
        lines: dict[int, list] = {}
        for w in words:
            top_key = round(w.get("top", 0) / 5) * 5
            lines.setdefault(top_key, []).append(w)
        for top_key in sorted(lines.keys()):
            line_words = lines[top_key]
            line_text = " ".join(w["text"] for w in line_words)
            line_size = sum(w.get("size", 12) for w in line_words) / len(line_words)
            if line_size > avg_size * 1.3 and len(line_words) <= 12 and len(line_text.strip()) > 2:
                headings.append(line_text.strip())
    except Exception:
        pass
    return headings[:5]


def _extract_tables(page) -> list[list[list[str]]]:
    tables = []
    try:
        raw_tables = page.extract_tables()
        if raw_tables:
            for tbl in raw_tables:
                cleaned = [
                    [str(cell).strip() if cell else "" for cell in row]
                    for row in tbl
                ]
                tables.append(cleaned)
    except Exception:
        pass
    return tables


def parse_pdf(pdf_path: str) -> ParsedDeck:
    slides: list[SlideData] = []
    all_text_parts: list[str] = []
    all_numbers: list[str] = []

    import fitz
    fitz_doc = fitz.open(pdf_path)

    # Collect all slide texts first
    slide_texts = []
    with pdfplumber.open(pdf_path) as pdf:
        raw_pages = []
        for idx, page in enumerate(pdf.pages):
            raw_text = page.extract_text() or ""
            # If pdfplumber got less than 30 chars, fall back to PyMuPDF
            if len(raw_text.strip()) < 30:
                try:
                    fitz_page = fitz_doc[idx]
                    raw_text = fitz_page.get_text("text") or ""
                except Exception:
                    pass

            # If still no text, use OCR on the rendered page image
            if len(raw_text.strip()) < 30:
                try:
                    import pytesseract
                    from PIL import Image
                    import io
                    fitz_page = fitz_doc[idx]
                    pix = fitz_page.get_pixmap(dpi=200)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    raw_text = pytesseract.image_to_string(img) or ""
                except Exception:
                    pass
            raw_pages.append((idx, page, raw_text))
            slide_texts.append(raw_text[:2000] if raw_text else "")

    # Batch embed all slides at once (much faster than one by one)
    batch_category_scores = []
    try:
        co = _get_cohere()
        ref_embeddings = _get_reference_embeddings()

        valid_texts = [t if t.strip() else "empty slide" for t in slide_texts]
        response = co.embed(
            texts=valid_texts,
            model="embed-english-v3.0",
            input_type="search_query",
        )
        slide_embeddings = response.embeddings

        for slide_emb in slide_embeddings:
            category_sims: dict[str, list[float]] = {cat: [] for cat in CATEGORY_DESCRIPTIONS}
            for ref_emb, label in zip(ref_embeddings, _CATEGORY_LABELS):
                sim = _cosine_similarity(slide_emb, ref_emb)
                category_sims[label].append(sim)
            final = {}
            for cat, sims in category_sims.items():
                max_sim = max(sims) if sims else 0.0
                normalized = max(0.0, (max_sim - 0.35) / 0.40) * 10
                final[cat] = round(min(normalized, 10.0), 2)
            batch_category_scores.append(final)

    except Exception:
        # Fallback: all zeros
        batch_category_scores = [{cat: 0.0 for cat in CATEGORY_DESCRIPTIONS} for _ in slide_texts]

    # Now build slide data
    with pdfplumber.open(pdf_path) as pdf:
        for idx, page in enumerate(pdf.pages):
            _, _, raw_text = raw_pages[idx]
            slide_num = idx + 1
            all_text_parts.append(raw_text)

            word_count = len(raw_text.split())
            numeric_values = _extract_numeric_values(raw_text)
            tables = _extract_tables(page)
            heading_hints = _extract_heading_hints(page)
            category_scores = batch_category_scores[idx]

            for vals in numeric_values.values():
                all_numbers.extend(vals)

            sorted_cats = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
            primary = sorted_cats[0][0] if sorted_cats[0][1] > 0 else "Unknown"
            secondary = sorted_cats[1][0] if len(sorted_cats) > 1 and sorted_cats[1][1] > 0 else None

            slides.append(SlideData(
                slide_number=slide_num,
                raw_text=raw_text,
                word_count=word_count,
                numeric_values=numeric_values,
                tables=tables,
                primary_category=primary,
                secondary_category=secondary,
                category_scores=category_scores,
                heading_hints=heading_hints,
            ))

    fitz_doc.close()

    category_slide_map: dict[str, list[int]] = {}
    for slide in slides:
        cat = slide.primary_category
        category_slide_map.setdefault(cat, []).append(slide.slide_number)

    return ParsedDeck(
        slides=slides,
        total_slides=len(slides),
        all_text=" ".join(all_text_parts),
        all_numbers=list(set(all_numbers)),
        category_slide_map=category_slide_map,
    )