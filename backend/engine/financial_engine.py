"""
financial_engine.py
All rule-based, deterministic financial checks. No AI used here.
Every check returns structured evidence with slide citations.
"""

import re
from dataclasses import dataclass, field
from typing import Optional
from parser.pdf_parser import ParsedDeck


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    check_name: str
    result: str          # "pass" | "warn" | "fail" | "insufficient_data"
    slide_number: Optional[int]
    evidence_text: Optional[str]
    rule_applied: str
    severity: int        # 1=low, 2=medium, 3=high
    detail: str


@dataclass
class FinancialReport:
    checks: list[CheckResult]
    pass_count: int
    warn_count: int
    fail_count: int
    skipped_count: int
    summary: str


# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

def _parse_money(text: str) -> Optional[float]:
    """Convert '$3.2M', '$500K', '$1B', '3,200,000' to a float in USD."""
    text = text.strip().replace(",", "")
    m = re.search(r'\$?([\d.]+)\s*([kmb])?', text, re.IGNORECASE)
    if not m:
        return None
    num = float(m.group(1))
    suffix = (m.group(2) or "").lower()
    if suffix == "k":
        num *= 1_000
    elif suffix == "m":
        num *= 1_000_000
    elif suffix == "b":
        num *= 1_000_000_000
    return num


def _find_in_slides(deck: ParsedDeck, patterns: list[str]) -> list[tuple[int, str, str]]:
    """
    Search all slides for any of the given regex patterns.
    Returns list of (slide_number, matched_text, context).
    """
    hits = []
    for slide in deck.slides:
        text = slide.raw_text
        for pat in patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                start = max(0, m.start() - 60)
                end = min(len(text), m.end() + 60)
                context = text[start:end].replace("\n", " ").strip()
                hits.append((slide.slide_number, m.group(0), context))
    return hits


def _extract_percentages_near(text: str, keyword: str) -> list[float]:
    """Find percentages within 200 chars of a keyword."""
    results = []
    for m in re.finditer(re.escape(keyword), text, re.IGNORECASE):
        window = text[max(0, m.start()-100):m.end()+100]
        for pct in re.findall(r'(\d+(?:\.\d+)?)\s*%', window):
            results.append(float(pct))
    return results


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_growth_rate_sanity(deck: ParsedDeck) -> CheckResult:
    """Flag revenue/user growth claims above 300% YoY."""
    hits = _find_in_slides(deck, [
        r'(\d{3,}(?:\.\d+)?)\s*%\s*(?:growth|increase|yoy|year.over.year)',
        r'(?:growth|increase|yoy)\s*(?:of\s+)?(\d{3,}(?:\.\d+)?)\s*%',
    ])
    if not hits:
        return CheckResult(
            check_name="Growth Rate Sanity",
            result="insufficient_data",
            slide_number=None,
            evidence_text=None,
            rule_applied="No YoY growth rates found in deck",
            severity=1,
            detail="No explicit year-over-year growth percentages were detected.",
        )

    worst_slide, worst_val, worst_ctx = None, 0.0, ""
    for slide_num, val_str, ctx in hits:
        nums = re.findall(r'(\d+(?:\.\d+)?)', val_str)
        for n in nums:
            v = float(n)
            if v > worst_val:
                worst_val = v
                worst_slide = slide_num
                worst_ctx = ctx

    if worst_val >= 1000:
        return CheckResult(
            check_name="Growth Rate Sanity",
            result="fail",
            slide_number=worst_slide,
            evidence_text=worst_ctx,
            rule_applied="Growth rate ≥ 1000% YoY is an automatic fail",
            severity=3,
            detail=f"Detected a {worst_val:.0f}% growth claim. Growth above 1000% YoY is extraordinary and will trigger immediate investor skepticism without detailed justification.",
        )
    if worst_val >= 300:
        return CheckResult(
            check_name="Growth Rate Sanity",
            result="warn",
            slide_number=worst_slide,
            evidence_text=worst_ctx,
            rule_applied="Growth rate above 300% YoY flagged as requiring justification",
            severity=2,
            detail=f"Detected a {worst_val:.0f}% growth claim. Claims above 300% YoY require explicit catalysts, market timing, or comparable benchmarks to be credible.",
        )
    return CheckResult(
        check_name="Growth Rate Sanity",
        result="pass",
        slide_number=worst_slide,
        evidence_text=worst_ctx,
        rule_applied="Growth rate within plausible range (< 300% YoY)",
        severity=1,
        detail=f"Highest detected growth rate is {worst_val:.0f}%, which is within a defensible range.",
    )


def check_burn_rate_consistency(deck: ParsedDeck) -> CheckResult:
    """Check runway = cash / burn math."""
    burn_hits = _find_in_slides(deck, [
        r'burn(?:\s+rate)?\s+(?:of\s+)?\$[\d,.]+[kmb]?',
        r'\$[\d,.]+[kmb]?\s+(?:monthly\s+)?burn',
    ])
    runway_hits = _find_in_slides(deck, [
        r'(\d+)\s+months?\s+(?:of\s+)?runway',
        r'runway\s+(?:of\s+)?(\d+)\s+months?',
    ])
    cash_hits = _find_in_slides(deck, [
        r'(?:cash|raised|raise)\s+(?:of\s+)?\$[\d,.]+[kmb]?',
        r'\$[\d,.]+[kmb]?\s+(?:in\s+)?(?:cash|the\s+bank)',
    ])

    if not burn_hits or not runway_hits:
        return CheckResult(
            check_name="Burn Rate Consistency",
            result="insufficient_data",
            slide_number=None,
            evidence_text=None,
            rule_applied="Burn rate or runway not found",
            severity=1,
            detail="Could not find both burn rate and runway figures to verify consistency.",
        )

    # Extract burn and runway values
    burn_val = None
    for slide_num, val_str, ctx in burn_hits:
        m = re.search(r'\$([\d,.]+)\s*([kmb])?', val_str, re.IGNORECASE)
        if m:
            raw = m.group(1).replace(",", "")
            suffix = (m.group(2) or "").lower()
            v = float(raw)
            if suffix == "k":
                v *= 1000
            elif suffix == "m":
                v *= 1_000_000
            burn_val = v
            burn_slide = slide_num
            break

    runway_val = None
    for slide_num, val_str, ctx in runway_hits:
        nums = re.findall(r'(\d+)', val_str)
        if nums:
            runway_val = int(nums[0])
            runway_slide = slide_num
            break

    cash_val = None
    for slide_num, val_str, ctx in cash_hits:
        m = re.search(r'\$([\d,.]+)\s*([kmb])?', val_str, re.IGNORECASE)
        if m:
            raw = m.group(1).replace(",", "")
            suffix = (m.group(2) or "").lower()
            v = float(raw)
            if suffix == "k":
                v *= 1000
            elif suffix == "m":
                v *= 1_000_000
            cash_val = v
            break

    if burn_val and runway_val and cash_val:
        expected_runway = cash_val / burn_val
        diff_pct = abs(expected_runway - runway_val) / max(runway_val, 1) * 100
        if diff_pct > 15:
            return CheckResult(
                check_name="Burn Rate Consistency",
                result="fail",
                slide_number=burn_slide,
                evidence_text=f"Stated runway: {runway_val}mo | Cash: ${cash_val:,.0f} | Burn: ${burn_val:,.0f}/mo | Implied runway: {expected_runway:.1f}mo",
                rule_applied="Runway must equal cash ÷ burn within 15% tolerance",
                severity=3,
                detail=f"Math inconsistency detected. Cash ÷ burn = {expected_runway:.1f} months but stated runway is {runway_val} months ({diff_pct:.0f}% discrepancy). Investors will catch this immediately.",
            )
        return CheckResult(
            check_name="Burn Rate Consistency",
            result="pass",
            slide_number=burn_slide,
            evidence_text=f"Stated runway: {runway_val}mo | Cash: ${cash_val:,.0f} | Burn: ${burn_val:,.0f}/mo",
            rule_applied="Runway = cash ÷ burn within 15% tolerance",
            severity=1,
            detail="Burn rate and runway figures are mathematically consistent.",
        )

    return CheckResult(
        check_name="Burn Rate Consistency",
        result="insufficient_data",
        slide_number=None,
        evidence_text=None,
        rule_applied="Insufficient data for full burn/cash/runway cross-check",
        severity=1,
        detail="Found some burn or runway figures but not enough for a complete cross-check.",
    )


def check_revenue_projection_compounding(deck: ParsedDeck) -> CheckResult:
    """Check if multi-year revenue projections have a consistent CAGR."""
    # Look for year-labeled revenue figures like "2024: $1M, 2025: $3M, 2026: $9M"
    year_rev_pattern = r'(?:20\d{2})[^\d]*\$([\d.,]+)\s*([kmb])?'
    hits = _find_in_slides(deck, [year_rev_pattern])

    if len(hits) < 2:
        return CheckResult(
            check_name="Revenue Projection Compounding",
            result="insufficient_data",
            slide_number=None,
            evidence_text=None,
            rule_applied="Need ≥2 year-labeled revenue figures",
            severity=1,
            detail="Could not find multiple year-labeled revenue projections to verify compounding.",
        )

    # Extract values
    values = []
    for slide_num, val_str, ctx in hits:
        years_in_ctx = re.findall(r'20(\d{2})', ctx)
        m = re.search(r'\$([\d.,]+)\s*([kmb])?', ctx, re.IGNORECASE)
        if m and years_in_ctx:
            raw = m.group(1).replace(",", "")
            suffix = (m.group(2) or "").lower()
            v = float(raw)
            if suffix == "k":
                v *= 1000
            elif suffix == "m":
                v *= 1_000_000
            elif suffix == "b":
                v *= 1_000_000_000
            values.append((int("20" + years_in_ctx[0]), v, slide_num, ctx))

    values.sort(key=lambda x: x[0])
    if len(values) < 2:
        return CheckResult(
            check_name="Revenue Projection Compounding",
            result="insufficient_data",
            slide_number=None,
            evidence_text=None,
            rule_applied="Insufficient parseable year-revenue pairs",
            severity=1,
            detail="Could not parse enough year-labeled revenue projections.",
        )

    # Check for hockey stick or inconsistency
    growth_rates = []
    for i in range(1, len(values)):
        prev_yr, prev_rev, _, _ = values[i-1]
        curr_yr, curr_rev, slide_num, ctx = values[i]
        if prev_rev > 0:
            growth = ((curr_rev / prev_rev) - 1) * 100
            growth_rates.append((curr_yr, growth, slide_num, ctx))

    max_growth = max(g for _, g, _, _ in growth_rates) if growth_rates else 0
    min_growth = min(g for _, g, _, _ in growth_rates) if growth_rates else 0

    # Flag extreme inconsistency (hockey stick)
    if max_growth > 500 and min_growth < 50:
        slide = growth_rates[0][2]
        ctx = growth_rates[0][3]
        return CheckResult(
            check_name="Revenue Projection Compounding",
            result="warn",
            slide_number=slide,
            evidence_text=ctx[:200],
            rule_applied="Inconsistent CAGR across projection years suggests hockey stick",
            severity=2,
            detail=f"Revenue growth rates vary from {min_growth:.0f}% to {max_growth:.0f}% YoY across projections. This hockey stick pattern requires explicit catalyst explanation.",
        )

    return CheckResult(
        check_name="Revenue Projection Compounding",
        result="pass",
        slide_number=values[-1][2],
        evidence_text=f"Analyzed {len(values)} revenue data points across {values[-1][0]-values[0][0]} years",
        rule_applied="Revenue compounding is internally consistent",
        severity=1,
        detail=f"Revenue projections imply a CAGR ranging from {min_growth:.0f}% to {max_growth:.0f}%, which is internally consistent.",
    )


def check_missing_cost_structure(deck: ParsedDeck) -> CheckResult:
    """Flag if revenue projections exist but no cost/expense breakdown."""
    has_revenue = bool(_find_in_slides(deck, [
        r'revenue\s+(?:projection|forecast|model)',
        r'projected\s+revenue',
        r'20\d{2}[^\d]*\$[\d.,]+[kmb]?',
    ]))

    has_costs = bool(_find_in_slides(deck, [
        r'\bcogs\b', r'cost of goods', r'operating expenses?', r'opex',
        r'cost structure', r'cost breakdown', r'gross margin', r'expenses',
        r'overhead', r'salaries', r'headcount cost',
    ]))

    if not has_revenue:
        return CheckResult(
            check_name="Missing Cost Structure",
            result="insufficient_data",
            slide_number=None,
            evidence_text=None,
            rule_applied="No revenue projections found to trigger check",
            severity=1,
            detail="No revenue projections detected; cost structure check not applicable.",
        )

    if not has_costs:
        return CheckResult(
            check_name="Missing Cost Structure",
            result="fail",
            slide_number=None,
            evidence_text="Revenue projections present but no cost breakdown detected",
            rule_applied="Revenue projections require accompanying cost structure",
            severity=3,
            detail="Revenue projections are present but there is no mention of COGS, operating expenses, or cost breakdown. Investors need to see how you get to the bottom line.",
        )

    return CheckResult(
        check_name="Missing Cost Structure",
        result="pass",
        slide_number=None,
        evidence_text="Both revenue projections and cost structure detected",
        rule_applied="Cost structure accompanies revenue projections",
        severity=1,
        detail="Revenue projections are accompanied by cost structure information.",
    )


def check_headcount_revenue_plausibility(deck: ParsedDeck) -> CheckResult:
    """Revenue per employee above $2M for early-stage is implausible."""
    team_hits = _find_in_slides(deck, [
        r'(?:team\s+of|currently\s+)(\d+)\s+(?:people|employees|members|engineers|headcount)',
        r'(\d+)\s+(?:full.?time|fte)',
    ])
    revenue_hits = _find_in_slides(deck, [
        r'(?:revenue|arr|mrr)\s+(?:of\s+)?\$[\d,.]+[kmb]?',
        r'\$[\d,.]+[kmb]?\s+(?:in\s+)?(?:revenue|arr|mrr)',
    ])

    if not team_hits or not revenue_hits:
        return CheckResult(
            check_name="Headcount to Revenue Plausibility",
            result="insufficient_data",
            slide_number=None,
            evidence_text=None,
            rule_applied="Team size or revenue not both found",
            severity=1,
            detail="Could not find both headcount and revenue figures for this check.",
        )

    headcount = None
    team_slide = None
    for slide_num, val_str, ctx in team_hits:
        nums = re.findall(r'(\d+)', val_str)
        if nums:
            headcount = int(nums[0])
            team_slide = slide_num
            team_ctx = ctx
            break

    revenue = None
    for slide_num, val_str, ctx in revenue_hits:
        m = re.search(r'\$([\d,.]+)\s*([kmb])?', val_str, re.IGNORECASE)
        if m:
            raw = m.group(1).replace(",", "")
            suffix = (m.group(2) or "").lower()
            v = float(raw)
            if suffix == "k":
                v *= 1000
            elif suffix == "m":
                v *= 1_000_000
            elif suffix == "b":
                v *= 1_000_000_000
            revenue = v
            break

    if headcount and revenue:
        rev_per_emp = revenue / headcount
        if rev_per_emp > 2_000_000:
            return CheckResult(
                check_name="Headcount to Revenue Plausibility",
                result="warn",
                slide_number=team_slide,
                evidence_text=f"Team: {headcount} people | Revenue: ${revenue:,.0f} | Revenue/employee: ${rev_per_emp:,.0f}",
                rule_applied="Revenue per employee > $2M flags as implausible for early-stage",
                severity=2,
                detail=f"Implied revenue per employee of ${rev_per_emp:,.0f} is above the $2M threshold. This suggests either the team size is understated or revenue projections are overstated.",
            )
        return CheckResult(
            check_name="Headcount to Revenue Plausibility",
            result="pass",
            slide_number=team_slide,
            evidence_text=f"Team: {headcount} | Revenue: ${revenue:,.0f} | Rev/emp: ${rev_per_emp:,.0f}",
            rule_applied="Revenue per employee ≤ $2M",
            severity=1,
            detail=f"Revenue per employee (${rev_per_emp:,.0f}) is within a plausible range.",
        )

    return CheckResult(
        check_name="Headcount to Revenue Plausibility",
        result="insufficient_data",
        slide_number=None,
        evidence_text=None,
        rule_applied="Could not parse numeric values",
        severity=1,
        detail="Found headcount and revenue mentions but could not parse numeric values for comparison.",
    )


def check_market_size_logic(deck: ParsedDeck) -> CheckResult:
    """TAM > SAM > SOM hierarchy check, and SOM capture sanity."""
    tam_hits = _find_in_slides(deck, [r'tam\b[^\d]*\$?([\d,.]+)\s*([kmbt])?', r'total addressable[^\d]*\$?([\d,.]+)\s*([kmbt])?'])
    sam_hits = _find_in_slides(deck, [r'sam\b[^\d]*\$?([\d,.]+)\s*([kmbt])?', r'serviceable addressable[^\d]*\$?([\d,.]+)\s*([kmbt])?'])
    som_hits = _find_in_slides(deck, [r'som\b[^\d]*\$?([\d,.]+)\s*([kmbt])?', r'serviceable obtainable[^\d]*\$?([\d,.]+)\s*([kmbt])?'])

    def parse_first_hit(hits):
        for slide_num, val_str, ctx in hits:
            m = re.search(r'([\d,.]+)\s*([kmbt])?', val_str)
            if m:
                raw = m.group(1).replace(",", "")
                suffix = (m.group(2) or "").lower()
                try:
                    v = float(raw)
                except ValueError:
                    continue
                if suffix == "k":
                    v *= 1000
                elif suffix == "m":
                    v *= 1_000_000
                elif suffix in ("b", "t"):
                    v *= 1_000_000_000
                return v, slide_num, ctx
        return None, None, None

    tam, tam_slide, tam_ctx = parse_first_hit(tam_hits)
    sam, sam_slide, sam_ctx = parse_first_hit(sam_hits)
    som, som_slide, som_ctx = parse_first_hit(som_hits)

    if not any([tam, sam, som]):
        return CheckResult(
            check_name="Market Size Logic",
            result="insufficient_data",
            slide_number=None,
            evidence_text=None,
            rule_applied="No TAM/SAM/SOM figures found",
            severity=1,
            detail="No TAM, SAM, or SOM figures were detected in the deck.",
        )

    if tam and sam and som:
        if not (tam >= sam >= som):
            return CheckResult(
                check_name="Market Size Logic",
                result="fail",
                slide_number=tam_slide,
                evidence_text=f"TAM: ${tam:,.0f} | SAM: ${sam:,.0f} | SOM: ${som:,.0f}",
                rule_applied="TAM ≥ SAM ≥ SOM hierarchy must hold",
                severity=3,
                detail=f"Market size hierarchy is violated. TAM must be ≥ SAM ≥ SOM. Your figures: TAM=${tam:,.0f}, SAM=${sam:,.0f}, SOM=${som:,.0f}.",
            )
        som_of_tam = (som / tam) * 100
        if som_of_tam > 10:
            return CheckResult(
                check_name="Market Size Logic",
                result="warn",
                slide_number=som_slide,
                evidence_text=f"SOM is {som_of_tam:.1f}% of TAM",
                rule_applied="SOM capture rate > 10% of TAM is unrealistic for pre-revenue companies",
                severity=2,
                detail=f"Your SOM ({som_of_tam:.1f}% of TAM) is very high for a pre-revenue company. Investors expect early-stage companies to target a small beachhead, typically under 5% of TAM.",
            )
        return CheckResult(
            check_name="Market Size Logic",
            result="pass",
            slide_number=tam_slide,
            evidence_text=f"TAM: ${tam:,.0f} | SAM: ${sam:,.0f} | SOM: ${som:,.0f}",
            rule_applied="TAM ≥ SAM ≥ SOM hierarchy holds and SOM capture ≤ 10%",
            severity=1,
            detail="Market size hierarchy is correct and SOM capture rate is reasonable.",
        )

    return CheckResult(
        check_name="Market Size Logic",
        result="warn",
        slide_number=None,
        evidence_text=f"Partial market data: TAM={'found' if tam else 'missing'}, SAM={'found' if sam else 'missing'}, SOM={'found' if som else 'missing'}",
        rule_applied="All three of TAM, SAM, SOM should be present",
        severity=2,
        detail="Not all of TAM, SAM, and SOM are stated. Investors expect all three with clear methodology.",
    )


def check_runway(deck: ParsedDeck) -> CheckResult:
    """Flag runway < 12 months post-raise."""
    hits = _find_in_slides(deck, [
        r'(\d+)\s+months?\s+(?:of\s+)?runway',
        r'runway\s+(?:of\s+)?(\d+)\s+months?',
        r'runway[:\s]+(\d+)',
    ])
    if not hits:
        return CheckResult(
            check_name="Runway Check",
            result="insufficient_data",
            slide_number=None,
            evidence_text=None,
            rule_applied="No runway figure found",
            severity=1,
            detail="No runway figure was detected in the deck.",
        )

    for slide_num, val_str, ctx in hits:
        nums = re.findall(r'(\d+)', val_str)
        if nums:
            runway_months = int(nums[0])
            if runway_months < 12:
                return CheckResult(
                    check_name="Runway Check",
                    result="fail",
                    slide_number=slide_num,
                    evidence_text=ctx,
                    rule_applied="Post-raise runway must be ≥ 12 months",
                    severity=3,
                    detail=f"Stated runway of {runway_months} months is below the 12-month minimum. Investors want to see at least 18 months to give the company time to hit milestones and raise the next round.",
                )
            return CheckResult(
                check_name="Runway Check",
                result="pass",
                slide_number=slide_num,
                evidence_text=ctx,
                rule_applied="Runway ≥ 12 months post-raise",
                severity=1,
                detail=f"Stated runway of {runway_months} months meets the minimum threshold.",
            )

    return CheckResult(
        check_name="Runway Check",
        result="insufficient_data",
        slide_number=None,
        evidence_text=None,
        rule_applied="Runway mention found but value not parseable",
        severity=1,
        detail="Runway was mentioned but a numeric value could not be extracted.",
    )


def check_round_size_vs_valuation(deck: ParsedDeck) -> CheckResult:
    """Check implied dilution (raise/valuation) is between 5% and 40%."""
    raise_hits = _find_in_slides(deck, [
        r'raising\s+\$?([\d,.]+)\s*([kmb])?',
        r'raise\s+\$?([\d,.]+)\s*([kmb])?',
        r'seeking\s+\$?([\d,.]+)\s*([kmb])?',
        r'round\s+(?:size\s+)?\$?([\d,.]+)\s*([kmb])?',
    ])
    val_hits = _find_in_slides(deck, [
        r'(?:pre.?money\s+)?valuation\s+(?:of\s+)?\$?([\d,.]+)\s*([kmb])?',
        r'\$?([\d,.]+)\s*([kmb])?\s+(?:pre.?money\s+)?valuation',
    ])

    def parse_amount(hits):
        for slide_num, val_str, ctx in hits:
            m = re.search(r'([\d,.]+)\s*([kmb])?', val_str)
            if m:
                raw = m.group(1).replace(",", "")
                suffix = (m.group(2) or "").lower()
                try:
                    v = float(raw)
                except ValueError:
                    continue
                if suffix == "k":
                    v *= 1000
                elif suffix == "m":
                    v *= 1_000_000
                elif suffix == "b":
                    v *= 1_000_000_000
                return v, slide_num, ctx
        return None, None, None

    raise_amt, raise_slide, raise_ctx = parse_amount(raise_hits)
    valuation, val_slide, val_ctx = parse_amount(val_hits)

    if not raise_amt or not valuation:
        return CheckResult(
            check_name="Round Size vs Valuation",
            result="insufficient_data",
            slide_number=None,
            evidence_text=None,
            rule_applied="Raise amount and/or valuation not found",
            severity=1,
            detail="Could not find both raise amount and valuation for dilution check.",
        )

    dilution = (raise_amt / (valuation + raise_amt)) * 100
    if dilution < 5:
        return CheckResult(
            check_name="Round Size vs Valuation",
            result="warn",
            slide_number=raise_slide,
            evidence_text=f"Raise: ${raise_amt:,.0f} | Valuation: ${valuation:,.0f} | Implied dilution: {dilution:.1f}%",
            rule_applied="Implied dilution < 5% is unusually low",
            severity=2,
            detail=f"Implied dilution of {dilution:.1f}% is very low. This could indicate an inflated valuation. Standard seed rounds dilute 10-25%.",
        )
    if dilution > 40:
        return CheckResult(
            check_name="Round Size vs Valuation",
            result="warn",
            slide_number=raise_slide,
            evidence_text=f"Raise: ${raise_amt:,.0f} | Valuation: ${valuation:,.0f} | Implied dilution: {dilution:.1f}%",
            rule_applied="Implied dilution > 40% is unusually high",
            severity=2,
            detail=f"Implied dilution of {dilution:.1f}% is very high. This may leave founders with insufficient equity for future rounds. Typical seed: 10-25%.",
        )
    return CheckResult(
        check_name="Round Size vs Valuation",
        result="pass",
        slide_number=raise_slide,
        evidence_text=f"Raise: ${raise_amt:,.0f} | Valuation: ${valuation:,.0f} | Dilution: {dilution:.1f}%",
        rule_applied="Implied dilution between 5% and 40%",
        severity=1,
        detail=f"Implied dilution of {dilution:.1f}% is within a reasonable range for this round size.",
    )


def check_hockey_stick_detection(deck: ParsedDeck) -> CheckResult:
    """Detect flat/decline then sudden exponential growth without a catalyst."""
    # Look for sequences of numbers that show flat then spike
    all_dollar_sequences = []
    for slide in deck.slides:
        amounts = re.findall(r'\$([\d,.]+)\s*([kmb])?', slide.raw_text, re.IGNORECASE)
        parsed = []
        for raw, suffix in amounts:
            try:
                v = float(raw.replace(",", ""))
                s = suffix.lower()
                if s == "k":
                    v *= 1000
                elif s == "m":
                    v *= 1_000_000
                elif s == "b":
                    v *= 1_000_000_000
                parsed.append(v)
            except ValueError:
                pass
        if len(parsed) >= 3:
            all_dollar_sequences.append((slide.slide_number, parsed))

    for slide_num, seq in all_dollar_sequences:
        # Detect flat then spike: last value > 5x any earlier value, with earlier values close together
        max_early = max(seq[:-1])
        last = seq[-1]
        early_range = max(seq[:-1]) - min(seq[:-1])
        if last > max_early * 5 and early_range < max_early * 0.5:
            return CheckResult(
                check_name="Hockey Stick Detection",
                result="warn",
                slide_number=slide_num,
                evidence_text=f"Sequence detected: {[f'${v:,.0f}' for v in seq]}",
                rule_applied="Sudden 5x+ jump after flat progression without stated catalyst",
                severity=2,
                detail="A hockey stick projection was detected: numbers are flat then spike dramatically. Investors will ask for the specific catalyst. Add milestone, market event, or product launch that explains the inflection.",
            )

    return CheckResult(
        check_name="Hockey Stick Detection",
        result="pass",
        slide_number=None,
        evidence_text=None,
        rule_applied="No unexplained hockey stick patterns found",
        severity=1,
        detail="No extreme hockey stick patterns detected in financial projections.",
    )


def check_currency_unit_consistency(deck: ParsedDeck) -> CheckResult:
    """Check that all financial figures use consistent units."""
    # Detect mixed unit usage (e.g., $1,500,000 and $1.5M on same/adjacent slides)
    raw_large = 0
    raw_million_str = 0
    raw_thousand_str = 0

    for slide in deck.slides:
        text = slide.raw_text
        # Raw large numbers ($1,500,000 style)
        raw_large += len(re.findall(r'\$[\d]{1,3}(?:,[\d]{3}){2,}', text))
        # M-style
        raw_million_str += len(re.findall(r'\$[\d.]+\s*[mM](?:illion)?(?!\w)', text))
        # K-style
        raw_thousand_str += len(re.findall(r'\$[\d.]+\s*[kK](?!ilo|\w)', text))

    styles_used = sum([raw_large > 0, raw_million_str > 0, raw_thousand_str > 0])
    if styles_used >= 3:
        return CheckResult(
            check_name="Currency and Unit Consistency",
            result="fail",
            slide_number=None,
            evidence_text=f"Raw numbers: {raw_large} | M-style: {raw_million_str} | K-style: {raw_thousand_str}",
            rule_applied="Financial figures should use consistent notation",
            severity=2,
            detail="Three different number formats detected ($1,000,000 vs $1M vs $1K). Standardize all financial figures to one format (recommend millions with M suffix).",
        )
    if styles_used == 2:
        return CheckResult(
            check_name="Currency and Unit Consistency",
            result="warn",
            slide_number=None,
            evidence_text=f"Raw: {raw_large} | M: {raw_million_str} | K: {raw_thousand_str}",
            rule_applied="Mixed financial notation styles detected",
            severity=1,
            detail="Two different number notation styles detected. Consider standardizing to one format throughout the deck.",
        )
    return CheckResult(
        check_name="Currency and Unit Consistency",
        result="pass",
        slide_number=None,
        evidence_text=f"Consistent notation used across {raw_large + raw_million_str + raw_thousand_str} financial figures",
        rule_applied="Consistent unit notation throughout",
        severity=1,
        detail="Financial figures appear to use consistent notation.",
    )


def check_margin_plausibility(deck: ParsedDeck) -> CheckResult:
    """Flag implausible gross margins."""
    hits = _find_in_slides(deck, [
        r'gross\s+margin[s]?\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*%',
        r'(\d+(?:\.\d+)?)\s*%\s+gross\s+margin',
        r'margin[s]?\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*%',
    ])

    # Also check for software mention
    is_software = bool(_find_in_slides(deck, [r'\bsaas\b', r'software', r'platform']))

    if not hits:
        return CheckResult(
            check_name="Margin Plausibility",
            result="insufficient_data",
            slide_number=None,
            evidence_text=None,
            rule_applied="No gross margin figures found",
            severity=1,
            detail="No gross margin figures detected in the deck.",
        )

    for slide_num, val_str, ctx in hits:
        nums = re.findall(r'(\d+(?:\.\d+)?)', val_str)
        if nums:
            margin = float(nums[0])
            if margin < 0:
                return CheckResult(
                    check_name="Margin Plausibility",
                    result="warn",
                    slide_number=slide_num,
                    evidence_text=ctx,
                    rule_applied="Negative gross margin requires explicit explanation",
                    severity=2,
                    detail=f"Negative gross margin ({margin}%) detected. If intentional (e.g., marketplace subsidy phase), explain the path to positive margins explicitly.",
                )
            if margin > 95 and not is_software:
                return CheckResult(
                    check_name="Margin Plausibility",
                    result="warn",
                    slide_number=slide_num,
                    evidence_text=ctx,
                    rule_applied="Gross margin > 95% is implausible for non-software companies",
                    severity=2,
                    detail=f"Gross margin of {margin}% is extremely high for a non-software business. Industry benchmarks: SaaS 70-85%, Marketplace 50-70%, Hardware 30-50%.",
                )
            return CheckResult(
                check_name="Margin Plausibility",
                result="pass",
                slide_number=slide_num,
                evidence_text=ctx,
                rule_applied="Gross margin within plausible range",
                severity=1,
                detail=f"Gross margin of {margin}% is within a plausible range for this business type.",
            )

    return CheckResult(
        check_name="Margin Plausibility",
        result="insufficient_data",
        slide_number=None,
        evidence_text=None,
        rule_applied="Margin percentages found but not parseable",
        severity=1,
        detail="Margin mentions found but could not extract numeric values.",
    )


def check_ask_use_of_funds(deck: ParsedDeck) -> CheckResult:
    """Check that use of funds allocations sum to ~100%."""
    # Look for use of funds percentages
    uof_hits = _find_in_slides(deck, [
        r'use\s+of\s+funds?',
        r'use\s+of\s+proceeds',
        r'fund\s+allocation',
    ])

    if not uof_hits:
        has_ask = bool(_find_in_slides(deck, [r'raising', r'raise\s+\$', r'funding\s+ask']))
        if has_ask:
            return CheckResult(
                check_name="Ask vs Use of Funds",
                result="fail",
                slide_number=None,
                evidence_text="Funding ask detected but no use of funds breakdown found",
                rule_applied="Funding ask requires use of funds breakdown",
                severity=2,
                detail="A funding ask is present but no use of funds breakdown was found. Investors always ask where their money goes — add a clear allocation breakdown.",
            )
        return CheckResult(
            check_name="Ask vs Use of Funds",
            result="insufficient_data",
            slide_number=None,
            evidence_text=None,
            rule_applied="No funding ask or use of funds detected",
            severity=1,
            detail="No funding ask or use of funds section was detected.",
        )

    # Extract percentages from use of funds slide
    slide_num, _, ctx = uof_hits[0]
    # Look at the full slide text
    full_slide_text = ""
    for slide in deck.slides:
        if slide.slide_number == slide_num:
            full_slide_text = slide.raw_text
            break

    percentages = re.findall(r'(\d+(?:\.\d+)?)\s*%', full_slide_text)
    if percentages:
        pct_values = [float(p) for p in percentages]
        total = sum(pct_values)
        if abs(total - 100) > 10:
            return CheckResult(
                check_name="Ask vs Use of Funds",
                result="warn",
                slide_number=slide_num,
                evidence_text=f"Detected percentages: {percentages} — Sum: {total:.0f}%",
                rule_applied="Use of funds allocations should sum to ~100%",
                severity=2,
                detail=f"Use of funds percentages sum to {total:.0f}% instead of 100%. Either some allocations are missing or there's a math error.",
            )
        return CheckResult(
            check_name="Ask vs Use of Funds",
            result="pass",
            slide_number=slide_num,
            evidence_text=f"Allocations: {percentages} — Sum: {total:.0f}%",
            rule_applied="Use of funds allocations sum to approximately 100%",
            severity=1,
            detail=f"Use of funds percentages sum to {total:.0f}%, which is within the expected range.",
        )

    return CheckResult(
        check_name="Ask vs Use of Funds",
        result="warn",
        slide_number=slide_num,
        evidence_text=ctx,
        rule_applied="Use of funds section found but no percentages detected",
        severity=1,
        detail="A use of funds section was found but no specific percentage allocations were detected. Add explicit percentage breakdowns.",
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_financial_engine(deck: ParsedDeck) -> FinancialReport:
    checks = [
        check_growth_rate_sanity(deck),
        check_burn_rate_consistency(deck),
        check_revenue_projection_compounding(deck),
        check_missing_cost_structure(deck),
        check_headcount_revenue_plausibility(deck),
        check_market_size_logic(deck),
        check_runway(deck),
        check_round_size_vs_valuation(deck),
        check_hockey_stick_detection(deck),
        check_currency_unit_consistency(deck),
        check_margin_plausibility(deck),
        check_ask_use_of_funds(deck),
    ]

    pass_count = sum(1 for c in checks if c.result == "pass")
    warn_count = sum(1 for c in checks if c.result == "warn")
    fail_count = sum(1 for c in checks if c.result == "fail")
    skipped = sum(1 for c in checks if c.result == "insufficient_data")

    summary = (
        f"Ran {len(checks)} financial checks: "
        f"{pass_count} passed, {warn_count} warnings, {fail_count} failed, {skipped} skipped (insufficient data)."
    )

    return FinancialReport(
        checks=checks,
        pass_count=pass_count,
        warn_count=warn_count,
        fail_count=fail_count,
        skipped_count=skipped,
        summary=summary,
    )
