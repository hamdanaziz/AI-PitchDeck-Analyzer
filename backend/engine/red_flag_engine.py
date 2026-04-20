"""
red_flag_engine.py
Aggregates financial check failures and scoring gaps into unified red flags.
Every red flag includes slide citation, evidence, and fix suggestion.
"""

from dataclasses import dataclass, field
from typing import Optional
from engine.financial_engine import FinancialReport, CheckResult
from engine.scoring_engine import ScoringReport, SectionScore


SEVERITY_MAP = {
    1: "Low",
    2: "Medium",
    3: "High",
}

BENCHMARKS = {
    "Growth Rate Sanity": "Top-quartile SaaS companies grow 3x YoY at early stage (Bessemer Cloud Index). 300%+ requires comps.",
    "Burn Rate Consistency": "Runway = cash / monthly burn. Any discrepancy > 15% is a math error investors will catch.",
    "Revenue Projection Compounding": "Best-in-class SaaS: T2D3 (triple, triple, double, double, double). Flat-then-spike requires catalyst.",
    "Missing Cost Structure": "Every financial projection needs a cost structure. Without it, gross margin and path to profitability cannot be assessed.",
    "Headcount to Revenue Plausibility": "Typical SaaS revenue per employee: $150K–$500K. Above $2M flags as implausible for early stage.",
    "Market Size Logic": "TAM > SAM > SOM is a required hierarchy. Pre-revenue companies typically target <5% of TAM in year 1.",
    "Runway Check": "18–24 months of post-raise runway is the standard. Below 12 months leaves no buffer for missed milestones.",
    "Round Size vs Valuation": "Typical seed dilution: 10–25%. Pre-seed: 15–20%. Below 5% or above 40% triggers valuation questions.",
    "Hockey Stick Detection": "Projections must tie to specific catalysts: product launch, market event, distribution deal, or pricing change.",
    "Currency and Unit Consistency": "All financial figures should use one notation format. Mixed formats signal lack of polish.",
    "Margin Plausibility": "SaaS gross margins: 70–85%. Marketplace: 50–70%. Hardware: 30–50%. Professional services: 20–40%.",
    "Ask vs Use of Funds": "Use of funds must sum to 100% with clear category breakdown (product, sales, marketing, G&A, hiring).",
}

SCORING_BENCHMARKS = {
    "Problem": "Strong decks quantify the problem size and name a specific customer archetype. Vague problem = vague market.",
    "Solution": "Investors fund differentiated solutions. Without a clear moat or differentiator, the deck looks commodity.",
    "Market Size": "TAM/SAM/SOM with source citations is the standard. Unsourced market size claims are dismissed.",
    "Business Model": "LTV:CAC ratio, pricing, and unit economics are expected at seed stage. Missing = investor homework burden.",
    "Traction": "Traction is the single most weight-bearing section for early-stage investors. Timestamped metrics are required.",
    "Team": "Investors fund teams as much as ideas. Domain expertise and relevant background must be explicit.",
    "Financials": "Burn rate, runway, and a path to profitability are minimum requirements for any fundraising deck.",
    "Ask": "The ask slide must answer: how much, at what valuation, for what use, hitting what milestone.",
}

FIX_SUGGESTIONS = {
    "Growth Rate Sanity": "Add a 'why now' or 'growth catalyst' section that explains what specifically drives the projected growth rate. Reference comparable companies at similar stage.",
    "Burn Rate Consistency": "Recalculate runway as (current cash + raise amount) ÷ monthly burn. Update all three numbers so they are consistent on the same slide.",
    "Revenue Projection Compounding": "Add a CAGR or annual growth rate to each year-over-year transition in your projection table. Explain what drives each inflection.",
    "Missing Cost Structure": "Add a slide with COGS breakdown, gross margin %, and operating expense categories. Even a simple table (COGS, S&M, R&D, G&A) is sufficient.",
    "Headcount to Revenue Plausibility": "Either break revenue into per-customer unit economics to show how a small team serves many customers, or revise headcount/revenue to a more realistic ratio.",
    "Market Size Logic": "Reorder or recalculate so TAM > SAM > SOM. Add a penetration assumption to explain how you get from SAM to your SOM target (e.g., '5% of SAM in year 3').",
    "Runway Check": "Either increase the raise amount, reduce the stated burn rate, or reduce the projected runway. 18 months post-raise is the investor-expected minimum.",
    "Round Size vs Valuation": "Reconsider the valuation relative to the raise size. At seed, $500K–$2M on a $3M–$10M pre-money valuation is typical. Adjust to the 10–25% dilution range.",
    "Hockey Stick Detection": "Add an annotation to your projection chart identifying the specific inflection point and what causes it: 'Product launch Q2 2025', 'Enterprise channel activated', etc.",
    "Currency and Unit Consistency": "Pick one format (recommend millions: $1.5M, $3M, $9M) and apply it consistently across every financial figure in the deck.",
    "Margin Plausibility": "Add a gross margin build: Revenue - COGS = Gross Profit, with a clear gross margin %. Benchmark against your industry (SaaS: 70-85%) and explain any deviation.",
    "Ask vs Use of Funds": "Add a pie chart or table showing: Hiring X%, Product Y%, Sales & Marketing Z%, Operations W%. Ensure all percentages add to 100%.",
}

SECTION_FIX_SUGGESTIONS = {
    "Problem": "Quantify the problem with a stat (e.g., '$4.5B lost annually' or '60% of SMBs struggle with X'). Name the customer archetype explicitly.",
    "Solution": "Add a comparison slide or table showing how you're different from alternatives. State your core differentiator in one sentence.",
    "Market Size": "Source every market size figure with a citation (Gartner, Forrester, IBISWorld). Add a TAM/SAM/SOM funnel diagram.",
    "Business Model": "Add a pricing table with tiers. State your LTV:CAC ratio. Include a simple P&L or unit economics one-pager.",
    "Traction": "Add a graph showing user/revenue growth over time with X-axis timestamps. Include at least one named customer or a logo bar.",
    "Team": "Add each founder's photo, role, and 2-3 previous relevant positions. Call out any domain expertise explicitly.",
    "Financials": "Add a 3-year projection table (revenue, gross margin, operating expenses, EBITDA). State burn rate and runway on the same slide.",
    "Ask": "Structure the ask slide as: Amount, Valuation (pre-money), Use of Funds breakdown, and 12/18-month milestone this enables.",
}


@dataclass
class RedFlag:
    title: str
    severity: str              # "Low" | "Medium" | "High" | "Critical"
    slide_number: Optional[int]
    evidence_quote: Optional[str]
    rule_violated: str
    explanation: str
    fix_suggestion: str
    benchmark: Optional[str]
    source_engine: str         # "Financial Engine" | "Scoring Engine"


def _financial_check_to_red_flag(check: CheckResult) -> Optional[RedFlag]:
    if check.result not in ("warn", "fail"):
        return None

    severity_str = SEVERITY_MAP.get(check.severity, "Medium")
    if check.result == "fail" and check.severity == 3:
        severity_str = "Critical"
    elif check.result == "fail":
        severity_str = "High"

    return RedFlag(
        title=check.check_name,
        severity=severity_str,
        slide_number=check.slide_number,
        evidence_quote=check.evidence_text,
        rule_violated=check.rule_applied,
        explanation=check.detail,
        fix_suggestion=FIX_SUGGESTIONS.get(check.check_name, "Review this section and address the flagged issue."),
        benchmark=BENCHMARKS.get(check.check_name),
        source_engine="Financial Engine",
    )


def _section_score_to_red_flag(section: SectionScore) -> Optional[RedFlag]:
    if section.score >= 5.0:
        return None

    if section.score < 3:
        severity = "High"
    elif section.score < 5:
        severity = "Medium"
    else:
        severity = "Low"

    missed_str = ", ".join(section.criteria_missed) if section.criteria_missed else "multiple criteria"

    return RedFlag(
        title=f"Weak {section.section} Section",
        severity=severity,
        slide_number=section.slide_numbers[0] if section.slide_numbers else None,
        evidence_quote=f"Section score: {section.score}/10 — Missing: {missed_str}",
        rule_violated=f"{section.section} section scored below 5/10 threshold",
        explanation=f"The {section.section} section scored {section.score}/10. Missing: {missed_str}. {SCORING_BENCHMARKS.get(section.section, '')}",
        fix_suggestion=SECTION_FIX_SUGGESTIONS.get(section.section, f"Strengthen the {section.section} section with more specific evidence and data."),
        benchmark=SCORING_BENCHMARKS.get(section.section),
        source_engine="Scoring Engine",
    )


def run_red_flag_engine(
    financial_report: FinancialReport,
    scoring_report: ScoringReport,
) -> list[RedFlag]:
    flags: list[RedFlag] = []

    # Financial engine flags
    for check in financial_report.checks:
        flag = _financial_check_to_red_flag(check)
        if flag:
            flags.append(flag)

    # Scoring engine flags
    for section in scoring_report.sections:
        flag = _section_score_to_red_flag(section)
        if flag:
            flags.append(flag)

    # Sort: Critical > High > Medium > Low
    severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    flags.sort(key=lambda f: severity_order.get(f.severity, 4))

    return flags
