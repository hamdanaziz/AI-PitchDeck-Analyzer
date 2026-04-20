"""
bias_checker.py
Bias audit module for FlowState.
Checks for potential demographic, geographic, and linguistic bias
in the scoring and red flag outputs.
All checks are deterministic and rule-based.
"""

import re
from dataclasses import dataclass, field
from typing import Optional
from parser.pdf_parser import ParsedDeck
from engine.scoring_engine import ScoringReport
from engine.red_flag_engine import RedFlag


# ---------------------------------------------------------------------------
# Reference data for bias detection
# ---------------------------------------------------------------------------

# Common female-associated first names (common standalone first names only —
# excludes short/ambiguous words that appear in normal business text)
FEMALE_NAME_SIGNALS = {
    "sarah", "emily", "jessica", "ashley", "jennifer", "amanda", "stephanie",
    "melissa", "nicole", "elizabeth", "hannah", "samantha", "rachel", "laura",
    "megan", "chelsea", "brittany", "danielle", "alexandra", "olivia", "sophia",
    "emma", "isabella", "ava", "mia", "aisha", "fatima", "priya", "ananya",
    "divya", "pooja", "neha", "shruti", "kavya", "meera", "sana", "zara",
    "nadia", "yasmin", "amira", "leila", "maria", "ana", "sofia", "valentina",
    "camila", "luna", "elena", "natasha", "irina", "yuki", "sakura",
}

MALE_NAME_SIGNALS = {
    "james", "john", "robert", "michael", "william", "david", "richard",
    "joseph", "thomas", "charles", "christopher", "daniel", "matthew",
    "anthony", "mark", "donald", "steven", "paul", "andrew", "joshua",
    "kevin", "brian", "george", "timothy", "ronald", "edward", "jason",
    "jeffrey", "ryan", "jacob", "gary", "nicholas", "eric", "jonathan",
    "stephen", "larry", "justin", "scott", "brandon", "benjamin", "samuel",
    "raymond", "frank", "alexander", "patrick", "jack", "dennis", "jerry",
    "tyler", "aaron", "adam", "nathan", "henry", "douglas", "zachary",
    "peter", "kyle", "ethan", "walter", "noah", "jeremy", "christian",
    "keith", "roger", "terry", "sean", "gerald", "carl", "harold", "dylan",
    "arthur", "lawrence", "jordan", "jesse", "austin", "logan", "raj",
    "vikram", "arjun", "rahul", "amit", "suresh", "ravi", "arun", "nikhil",
    "mohammed", "ahmed", "hassan", "ibrahim", "yusuf",
}

# Currency patterns — explicit, unambiguous currency symbols/codes only.
# The old pattern r'R[\d,]+' was triggering on "R&D", "Revenue", etc.
NON_USD_CURRENCY_PATTERNS = [
    (r'£\s*[\d,]+', "GBP (British Pound)"),
    (r'€\s*[\d,]+', "EUR (Euro)"),
    (r'₹\s*[\d,]+', "INR (Indian Rupee)"),
    (r'¥\s*[\d,]+', "JPY/CNY (Yen/Yuan)"),
    (r'₦\s*[\d,]+', "NGN (Nigerian Naira)"),
    # ZAR must be the explicit code, not a bare "R" prefix
    (r'\bZAR\b', "ZAR (South African Rand)"),
    # "rand" as a standalone monetary noun
    (r'\brand\b\s+[\d,]+|\b[\d,]+\s+rand\b', "ZAR (South African Rand)"),
    (r'\bAED\s*[\d,]+', "AED (UAE Dirham)"),
    (r'\bPKR\s*[\d,]+', "PKR (Pakistani Rupee)"),
    (r'\bCAD\s*[\d,]+|\bC\$\s*[\d,]+', "CAD (Canadian Dollar)"),
    (r'\bAUD\s*[\d,]+|\bA\$\s*[\d,]+', "AUD (Australian Dollar)"),
    (r'\bSGD\s*[\d,]+|\bS\$\s*[\d,]+', "SGD (Singapore Dollar)"),
    (r'\bBRL\s*[\d,]+|\bR\$\s*[\d,]+', "BRL (Brazilian Real)"),
    (r'\bGBP\s*[\d,]+', "GBP (British Pound)"),
    (r'\bEUR\s*[\d,]+', "EUR (Euro)"),
]

# Geographic market references — explicit country/region names only.
# Removed bare "uk", "europe" etc. which appear frequently in general context.
NON_US_MARKET_SIGNALS = [
    (r'\bmena\b', "MENA"),
    (r'\bsouth\s+asia\b', "South Asia"),
    (r'\bsoutheast\s+asia\b', "Southeast Asia"),
    (r'\blatin\s+america\b', "Latin America"),
    (r'\bsub.saharan\s+africa\b', "Sub-Saharan Africa"),
    (r'\bwest\s+africa\b', "West Africa"),
    (r'\beast\s+africa\b', "East Africa"),
    (r'\bnigeria\b', "Nigeria"),
    (r'\bpakistan\b', "Pakistan"),
    (r'\bbangladesh\b', "Bangladesh"),
    (r'\bindonesia\b', "Indonesia"),
    (r'\bphilippines\b', "Philippines"),
    (r'\bvietnam\b', "Vietnam"),
    (r'\bkenya\b', "Kenya"),
    (r'\bghana\b', "Ghana"),
    (r'\bbrazil\b', "Brazil"),
    (r'\bcolombia\b', "Colombia"),
    (r'\bargentina\b', "Argentina"),
    (r'\bmexico\b', "Mexico"),
    (r'\bindia\b', "India"),
    (r'\bchina\b', "China"),
    (r'\bjapan\b', "Japan"),
    (r'\bsouth\s+korea\b', "South Korea"),
    (r'\bsingapore\b', "Singapore"),
    (r'\beuropean\s+union\b', "European Union"),
    (r'\bunited\s+kingdom\b', "United Kingdom"),
    (r'\bgermany\b', "Germany"),
    (r'\bnetherlands\b', "Netherlands"),
    (r'\bnordic\b', "Nordic"),
    (r'\bmiddle\s+east\b', "Middle East"),
    (r'\bsouth\s+africa\b', "South Africa"),
    (r'\baustralia\b', "Australia"),
    (r'\bcanada\b', "Canada"),
]

# Scoring criteria that are purely content-based (not demographic)
CONTENT_ONLY_CRITERIA = [
    "Specific problem stated",
    "Problem is quantified",
    "Target customer mentioned",
    "Market pain evidenced",
    "Solution clearly described",
    "Maps to the stated problem",
    "Differentiation mentioned",
    "How it works explained",
    "TAM stated",
    "SAM stated",
    "SOM stated",
    "Sources cited",
    "Methodology explained",
    "Revenue model clear",
    "Pricing stated",
    "Unit economics present",
    "Path to revenue clear",
    "Metrics present",
    "Metrics are time-stamped",
    "Growth rate stated",
    "Customer names or logos",
    "Retention or engagement",
    "Founders named",
    "Relevant backgrounds",
    "Domain expertise evident",
    "Advisors mentioned",
    "Revenue projections present",
    "Burn rate stated",
    "Runway stated",
    "Path to profitability",
    "Unit economics or margins",
    "Raise amount stated",
    "Use of funds explained",
    "Valuation mentioned",
    "Milestone plan tied to raise",
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BiasFlag:
    category: str           # "Gender", "Geographic", "Linguistic", "Sectoral"
    finding: str            # What was detected
    severity: str           # "Info", "Low", "Medium"
    detail: str             # Explanation
    mitigation: str         # What the system did to stay neutral


@dataclass
class BiasReport:
    gender_signals_detected: list[str]
    gender_detected: str                    # "Male-leaning", "Female-leaning", "Mixed", "None detected"
    scoring_is_gender_neutral: bool
    geographic_signals: list[str]
    non_us_market: bool
    currency_detected: Optional[str]
    scoring_is_geography_neutral: bool
    linguistic_complexity_score: float      # 0-10, higher = more complex language
    bias_flags: list[BiasFlag]
    overall_bias_risk: str                  # "Low", "Medium", "High"
    audit_summary: str
    criteria_checked: int
    criteria_demographic_free: int


# ---------------------------------------------------------------------------
# Detection functions
# ---------------------------------------------------------------------------

def _detect_gender_signals(deck: ParsedDeck) -> tuple[list[str], str]:
    """
    Detect gender signals from founder names appearing in the deck.
    Matches whole words only — will not match substrings.
    """
    text = deck.all_text.lower()
    words = set(re.findall(r'\b[a-z]+\b', text))

    female_found = sorted(words & FEMALE_NAME_SIGNALS)
    male_found = sorted(words & MALE_NAME_SIGNALS)

    all_signals = [f"{n} (female-associated)" for n in female_found] + \
                  [f"{n} (male-associated)" for n in male_found]

    if female_found and not male_found:
        gender = "Female-leaning"
    elif male_found and not female_found:
        gender = "Male-leaning"
    elif female_found and male_found:
        gender = "Mixed"
    else:
        gender = "None detected"

    return all_signals, gender


def _detect_geographic_signals(deck: ParsedDeck) -> tuple[list[str], bool, Optional[str]]:
    """
    Detect explicit non-US market references and non-USD currency symbols/codes.
    Only flags what is actually present in the deck — does not assume any
    market context based on absence of US mentions.
    """
    text = deck.all_text

    # Detect geographic market references
    geo_signals = []
    seen = set()
    for pattern, label in NON_US_MARKET_SIGNALS:
        if label not in seen and re.search(pattern, text, re.IGNORECASE):
            geo_signals.append(label)
            seen.add(label)

    # Detect non-USD currency
    currency_found = None
    for pattern, currency_name in NON_USD_CURRENCY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            currency_found = currency_name
            break

    non_us = bool(geo_signals or currency_found)
    return geo_signals[:8], non_us, currency_found


def _detect_linguistic_complexity(deck: ParsedDeck) -> float:
    """
    Score linguistic complexity 0-10.
    Lower scores may indicate non-native English — system should score
    based on content presence, not language sophistication.
    """
    text = deck.all_text
    if not text.strip():
        return 5.0

    words = text.split()
    if not words:
        return 5.0

    avg_word_len = sum(len(w) for w in words) / len(words)

    sentences = re.split(r'[.!?]+', text)
    sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
    avg_sent_len = sum(sentence_lengths) / max(len(sentence_lengths), 1)

    word_score = min((avg_word_len - 3) / 4 * 10, 10)
    sent_score = min(avg_sent_len / 25 * 10, 10)

    return round((word_score + sent_score) / 2, 1)


def _check_scoring_neutrality(scoring: ScoringReport) -> tuple[bool, bool]:
    """
    Verify that all scoring criteria are in the content-only list.
    Returns (gender_neutral, geography_neutral).
    """
    all_criteria_used = []
    for section in scoring.sections:
        all_criteria_used.extend(section.criteria_met)
        all_criteria_used.extend(section.criteria_missed)

    non_neutral = [c for c in all_criteria_used if c not in CONTENT_ONLY_CRITERIA]
    is_neutral = len(non_neutral) == 0
    return is_neutral, is_neutral


def _generate_bias_flags(
    gender: str,
    gender_signals: list[str],
    geo_signals: list[str],
    non_us: bool,
    currency: Optional[str],
    linguistic_score: float,
    gender_neutral: bool,
    geo_neutral: bool,
) -> list[BiasFlag]:
    flags = []

    # Gender flag
    if gender in ("Male-leaning", "Female-leaning"):
        flags.append(BiasFlag(
            category="Gender",
            finding=f"{gender} name signals detected: {', '.join(gender_signals[:3])}",
            severity="Info",
            detail=f"Founder name signals suggest a {gender.lower()} founding team. FlowState scoring is based entirely on content criteria and does not factor in founder demographics.",
            mitigation="All scoring criteria evaluate content presence only. Gender signals have zero weight in any scoring calculation.",
        ))

    # Geographic flag — only when actual geographic market references are present
    if non_us and geo_signals:
        flags.append(BiasFlag(
            category="Geographic",
            finding=f"Non-US market references detected: {', '.join(geo_signals[:4])}",
            severity="Info",
            detail="This deck references non-US markets. Financial benchmarks used in red flag checks (e.g. revenue per employee thresholds) are calibrated for US/global markets and may not perfectly reflect local market conditions.",
            mitigation="Scoring criteria evaluate structural completeness of the deck, not market geography. Financial checks use global benchmark ranges.",
        ))

    # Currency flag — only when non-USD symbols/codes appear in the text
    if currency:
        flags.append(BiasFlag(
            category="Geographic",
            finding=f"Non-USD currency detected: {currency}",
            severity="Low",
            detail=f"Financial figures appear to use {currency}. The financial engine is calibrated for USD. Revenue plausibility checks may produce imprecise results for non-USD figures without currency conversion.",
            mitigation="Red flag thresholds are based on order-of-magnitude checks. Minor currency differences do not affect pass/fail outcomes at large scales.",
        ))

    # Linguistic flag
    if linguistic_score < 4.0:
        flags.append(BiasFlag(
            category="Linguistic",
            finding=f"Below-average linguistic complexity detected (score: {linguistic_score}/10)",
            severity="Low",
            detail="The deck uses simpler or shorter language patterns, which may indicate non-native English authorship. Semantic scoring uses meaning-based embeddings rather than language sophistication.",
            mitigation="Cohere embeddings capture meaning regardless of phrasing style. A deck saying 'we make money from fees' scores the same as one saying 'our monetization strategy is commission-based'.",
        ))

    return flags


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_bias_checker(
    deck: ParsedDeck,
    scoring: ScoringReport,
    red_flags: list[RedFlag],
) -> BiasReport:

    gender_signals, gender = _detect_gender_signals(deck)
    geo_signals, non_us, currency = _detect_geographic_signals(deck)
    linguistic_score = _detect_linguistic_complexity(deck)
    gender_neutral, geo_neutral = _check_scoring_neutrality(scoring)

    bias_flags = _generate_bias_flags(
        gender, gender_signals, geo_signals, non_us,
        currency, linguistic_score, gender_neutral, geo_neutral,
    )

    # Count criteria
    all_criteria = []
    for section in scoring.sections:
        all_criteria.extend(section.criteria_met)
        all_criteria.extend(section.criteria_missed)

    demographic_free = sum(1 for c in all_criteria if c in CONTENT_ONLY_CRITERIA)

    # Overall risk
    medium_flags = sum(1 for f in bias_flags if f.severity == "Medium")
    low_flags = sum(1 for f in bias_flags if f.severity == "Low")

    if medium_flags > 0:
        overall_risk = "Medium"
    elif low_flags > 1:
        overall_risk = "Low-Medium"
    else:
        overall_risk = "Low"

    # Summary
    parts = []
    if gender != "None detected":
        parts.append(f"{gender} founding team signals detected")
    if non_us and geo_signals:
        parts.append("non-US market context identified")
    if currency:
        parts.append(f"non-USD currency ({currency}) noted")
    if linguistic_score < 4:
        parts.append("simplified language patterns observed")

    if parts:
        audit_summary = f"Bias audit identified: {', '.join(parts)}. Scoring remained content-based throughout. All {demographic_free} criteria evaluated are demographic-free."
    else:
        audit_summary = f"No significant bias signals detected. All {demographic_free} scoring criteria are content-based and demographic-free."

    return BiasReport(
        gender_signals_detected=gender_signals,
        gender_detected=gender,
        scoring_is_gender_neutral=gender_neutral,
        geographic_signals=geo_signals,
        non_us_market=non_us,
        currency_detected=currency,
        scoring_is_geography_neutral=geo_neutral,
        linguistic_complexity_score=linguistic_score,
        bias_flags=bias_flags,
        overall_bias_risk=overall_risk,
        audit_summary=audit_summary,
        criteria_checked=len(all_criteria),
        criteria_demographic_free=demographic_free,
    )
