"""
metrics_tracker.py
Tracks quality metrics for each analysis session.
"""

from dataclasses import dataclass, field
from engine.financial_engine import FinancialReport
from engine.scoring_engine import ScoringReport
from engine.red_flag_engine import RedFlag
from ai.feedback_generator import FeedbackOutput


@dataclass
class SessionMetrics:
    total_red_flags: int
    red_flags_with_citations: int
    citation_accuracy_rate: float        # percentage
    financial_checks_run: int
    financial_checks_with_findings: int
    hallucinated_claims_detected: int
    weak_sections_count: int             # sections scoring < 5
    overall_confidence_score: float      # % of red flags with direct quote evidence


def compute_metrics(
    financial_report: FinancialReport,
    scoring_report: ScoringReport,
    red_flags: list[RedFlag],
    feedback: FeedbackOutput,
) -> SessionMetrics:
    total_flags = len(red_flags)

    flags_with_citations = sum(
        1 for f in red_flags
        if f.slide_number is not None and f.evidence_quote is not None
    )

    citation_rate = (flags_with_citations / total_flags * 100) if total_flags else 100.0

    checks_run = len(financial_report.checks)
    checks_with_findings = sum(
        1 for c in financial_report.checks
        if c.result in ("warn", "fail")
    )

    hallucinations = len(feedback.hallucination_warnings)

    weak_sections = sum(1 for s in scoring_report.sections if s.score < 5.0)

    # Confidence: % of red flags that have BOTH slide number AND evidence quote
    flags_with_both = sum(
        1 for f in red_flags
        if f.slide_number is not None
        and f.evidence_quote is not None
        and len(f.evidence_quote) > 10
    )
    confidence = (flags_with_both / total_flags * 100) if total_flags else 100.0

    return SessionMetrics(
        total_red_flags=total_flags,
        red_flags_with_citations=flags_with_citations,
        citation_accuracy_rate=round(citation_rate, 1),
        financial_checks_run=checks_run,
        financial_checks_with_findings=checks_with_findings,
        hallucinated_claims_detected=hallucinations,
        weak_sections_count=weak_sections,
        overall_confidence_score=round(confidence, 1),
    )
