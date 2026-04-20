"""
main.py
FlowState AI — FastAPI backend
POST /analyze — accepts PDF upload, runs full analysis pipeline
"""
from dotenv import load_dotenv
load_dotenv()

import os
import re
import sys
import tempfile
import traceback
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Any

# Ensure local modules are on path
sys.path.insert(0, str(Path(__file__).parent))

from parser.deck_validator import validate_pitch_deck
from parser.pdf_parser import parse_pdf
from engine.financial_engine import run_financial_engine
from engine.scoring_engine import run_scoring_engine
from engine.red_flag_engine import run_red_flag_engine
from ai.feedback_generator import generate_feedback
from evaluation.metrics_tracker import compute_metrics


app = FastAPI(title="FlowState AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _serialize(obj: Any) -> Any:
    """Recursively convert dataclass instances to dicts for JSON serialization."""
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _serialize(v) for k, v in obj.__dict__.items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


def _metric_context(text: str, start: int, end: int) -> str:
    """Return a compact evidence quote around a detected metric."""
    snippet = text[max(0, start - 90):min(len(text), end + 90)]
    return re.sub(r"\s+", " ", snippet).strip()


def _find_metric(deck, label: str, key: str, patterns: list[str]) -> dict:
    """
    Deterministically find a business metric in parsed slide text.
    This is deliberately rule-based so displayed metrics are traceable to deck evidence.
    """
    for slide in deck.slides:
        text = slide.raw_text or ""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            value = match.group("value") if "value" in match.groupdict() else match.group(0)
            return {
                "key": key,
                "label": label,
                "value": re.sub(r"\s+", " ", value).strip(),
                "status": "found",
                "slide_number": slide.slide_number,
                "evidence": _metric_context(text, match.start(), match.end()),
            }

    return {
        "key": key,
        "label": label,
        "value": "Not found",
        "status": "missing",
        "slide_number": None,
        "evidence": "No explicit matching field was detected in the parsed deck text.",
    }


def _extract_key_metrics(deck) -> list[dict]:
    money = r"\$[\d,.]+(?:\s*[KMBTkmbt])?(?:illion|n)?"
    number = r"[\d,.]+(?:\s*[KMBTkmbt])?"
    percent = r"\d+(?:\.\d+)?\s*%"

    specs = [
        (
            "Startup Name",
            "startup_name",
            [
                r"(?P<value>[A-Z][A-Za-z0-9&.\-\s]{2,60})\s+(?:Pitch Deck|Investor Deck|Seed Deck|Series A)",
            ],
        ),
        (
            "Funding Ask",
            "funding_ask",
            [
                rf"(?:funding ask|raise amount|round size|raising|raise|seeking|investment sought)\s*(?:of|:)?\s*(?P<value>{money})",
                rf"(?P<value>{money})\s+(?:funding ask|raise|round|seed round|series a)",
            ],
        ),
        (
            "Valuation",
            "valuation",
            [
                rf"(?:valuation|pre-money valuation|post-money valuation|pre money valuation|post money valuation)\s*(?:of|:)?\s*(?P<value>{money})",
                rf"(?P<value>{money})\s+(?:valuation|pre-money|post-money|pre money|post money)",
            ],
        ),
        (
            "TAM",
            "tam",
            [
                rf"(?:\bTAM\b|total addressable market)\s*(?:of|:|=)?\s*(?P<value>{money})",
                rf"(?P<value>{money})\s+(?:\bTAM\b|total addressable market)",
            ],
        ),
        (
            "SAM",
            "sam",
            [
                rf"(?:\bSAM\b|serviceable addressable market)\s*(?:of|:|=)?\s*(?P<value>{money})",
                rf"(?P<value>{money})\s+(?:\bSAM\b|serviceable addressable market)",
            ],
        ),
        (
            "SOM",
            "som",
            [
                rf"(?:\bSOM\b|serviceable obtainable market)\s*(?:of|:|=)?\s*(?P<value>{money})",
                rf"(?P<value>{money})\s+(?:\bSOM\b|serviceable obtainable market)",
            ],
        ),
        (
            "ARR",
            "arr",
            [
                rf"(?:\bARR\b|annual recurring revenue)\s*(?:of|:|=)?\s*(?P<value>{money})",
                rf"(?P<value>{money})\s+(?:\bARR\b|annual recurring revenue)",
            ],
        ),
        (
            "MRR",
            "mrr",
            [
                rf"(?:\bMRR\b|monthly recurring revenue)\s*(?:of|:|=)?\s*(?P<value>{money})",
                rf"(?P<value>{money})\s+(?:\bMRR\b|monthly recurring revenue)",
            ],
        ),
        (
            "Revenue",
            "revenue",
            [
                rf"(?:revenue|sales)\s*(?:of|:|=)?\s*(?P<value>{money})",
                rf"(?P<value>{money})\s+(?:in\s+)?(?:revenue|sales)",
            ],
        ),
        (
            "Gross Margin",
            "gross_margin",
            [
                rf"(?:gross margin|gross margin %)\s*(?:of|:|=)?\s*(?P<value>{percent})",
                rf"(?P<value>{percent})\s+gross margin",
            ],
        ),
        (
            "Customers / Users",
            "customers",
            [
                rf"(?P<value>{number})\s+(?:paying\s+)?(?:customers|users|clients|subscribers)",
                rf"(?:customers|users|clients|subscribers)\s*(?:of|:|=)?\s*(?P<value>{number})",
            ],
        ),
        (
            "Cash Balance",
            "cash_balance",
            [
                rf"(?:cash balance|cash on hand|cash in bank|cash & cash equivalents|cash and cash equivalents)\s*(?:of|:|=)?\s*(?P<value>{money})",
                rf"(?P<value>{money})\s+(?:cash balance|cash on hand|cash in bank|cash)",
            ],
        ),
        (
            "Monthly Burn",
            "monthly_burn",
            [
                rf"(?:monthly burn|burn rate|cash burn)\s*(?:of|:|=)?\s*(?P<value>{money})",
                rf"(?P<value>{money})\s+(?:monthly burn|burn rate|cash burn|per month|/month)",
            ],
        ),
        (
            "Runway",
            "runway",
            [
                r"(?:runway)\s*(?:of|:|=)?\s*(?P<value>\d+(?:\.\d+)?\s*months?)",
                r"(?P<value>\d+(?:\.\d+)?\s*months?)\s+(?:of\s+)?runway",
            ],
        ),
    ]

    return [_find_metric(deck, label, key, patterns) for label, key, patterns in specs]


@app.get("/health")
async def health():
    return {"status": "ok", "service": "FlowState AI"}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted. Please upload a pitch deck in PDF format."
        )

    # Save upload to temp file
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")

    try:
        # ── Step 1: Validate ──────────────────────────────────────────────────
        validation = validate_pitch_deck(tmp_path)
        if not validation.is_valid:
            return JSONResponse(
                status_code=422,
                content={
                    "status": "rejected",
                    "reason": validation.rejection_reason,
                    "page_count": validation.page_count,
                    "keyword_matches": validation.keyword_matches,
                    "avg_words_per_page": validation.avg_words_per_page,
                }
            )

        # ── Step 2: Parse ─────────────────────────────────────────────────────
        try:
            deck = parse_pdf(tmp_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF parsing failed: {str(e)}")

        # ── Step 3: Financial Engine ──────────────────────────────────────────
        try:
            financial_report = run_financial_engine(deck)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Financial engine error: {str(e)}")

        # ── Step 3b: Key Extracted Metrics ───────────────────────────────────
        extracted_metrics = _extract_key_metrics(deck)

        # ── Step 4: Scoring Engine ────────────────────────────────────────────
        try:
            scoring_report = run_scoring_engine(deck)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Scoring engine error: {str(e)}")

        # ── Step 5: Red Flag Engine ───────────────────────────────────────────
        try:
            red_flags = run_red_flag_engine(financial_report, scoring_report)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Red flag engine error: {str(e)}")

        # ── Step 6: AI Feedback (Claude) ──────────────────────────────────────
        try:
            feedback = generate_feedback(financial_report, scoring_report, red_flags)
        except Exception as e:
            # AI feedback failure should not crash the whole report
            from ai.feedback_generator import FeedbackOutput
            feedback = FeedbackOutput(
                executive_summary=f"AI feedback unavailable: {str(e)}",
                section_narratives={s.section: s.summary for s in scoring_report.sections},
                priority_actions=[f.title for f in red_flags[:3]],
                hallucination_warnings=[f"AI error: {str(e)}"],
            )

        # ── Step 6b: Bias Check ───────────────────────────────────────────────
        try:
            from evaluation.bias_checker import run_bias_checker
            bias_report = run_bias_checker(deck, scoring_report, red_flags)
        except Exception as e:
            from evaluation.bias_checker import BiasReport
            bias_report = BiasReport(
                gender_signals_detected=[],
                gender_detected="Unknown",
                scoring_is_gender_neutral=True,
                geographic_signals=[],
                non_us_market=False,
                currency_detected=None,
                scoring_is_geography_neutral=True,
                linguistic_complexity_score=5.0,
                bias_flags=[],
                overall_bias_risk="Low",
                audit_summary=f"Bias check unavailable: {str(e)}",
                criteria_checked=0,
                criteria_demographic_free=0,
            )

        # ── Step 7: Metrics ───────────────────────────────────────────────────
        try:
            metrics = compute_metrics(financial_report, scoring_report, red_flags, feedback)
        except Exception as e:
            from evaluation.metrics_tracker import SessionMetrics
            metrics = SessionMetrics(
                total_red_flags=len(red_flags),
                red_flags_with_citations=0,
                citation_accuracy_rate=0.0,
                financial_checks_run=0,
                financial_checks_with_findings=0,
                hallucinated_claims_detected=0,
                weak_sections_count=0,
                overall_confidence_score=0.0,
            )

        # ── Assemble Response ─────────────────────────────────────────────────
        # Build slide map
        slide_map = []
        for slide in deck.slides:
            has_flags = any(
                f.slide_number == slide.slide_number for f in red_flags if f.slide_number
            )
            slide_map.append({
                "slide_number": slide.slide_number,
                "primary_category": slide.primary_category,
                "secondary_category": slide.secondary_category,
                "word_count": slide.word_count,
                "has_red_flags": has_flags,
                "heading_hints": slide.heading_hints,
            })

        response = {
            "status": "success",
            "filename": file.filename,
            "validation": {
                "page_count": validation.page_count,
                "confidence": validation.confidence,
                "keyword_matches": validation.keyword_matches,
                "avg_words_per_page": round(validation.avg_words_per_page, 1),
            },
            "scoring": {
                "overall_score": scoring_report.overall_score,
                "weighted_score": scoring_report.weighted_score,
                "weakest_sections": scoring_report.weakest_sections,
                "strongest_sections": scoring_report.strongest_sections,
                "sections": [
                    {
                        "section": s.section,
                        "score": s.score,
                        "weight": s.weight,
                        "criteria_met": s.criteria_met,
                        "criteria_missed": s.criteria_missed,
                        "slide_numbers": s.slide_numbers,
                        "summary": s.summary,
                        "narrative": feedback.section_narratives.get(s.section, ""),
                    }
                    for s in scoring_report.sections
                ],
            },
            "financial": {
                "summary": financial_report.summary,
                "pass_count": financial_report.pass_count,
                "warn_count": financial_report.warn_count,
                "fail_count": financial_report.fail_count,
                "skipped_count": financial_report.skipped_count,
                "checks": [
                    {
                        "check_name": c.check_name,
                        "result": c.result,
                        "slide_number": c.slide_number,
                        "evidence_text": c.evidence_text,
                        "rule_applied": c.rule_applied,
                        "severity": c.severity,
                        "detail": c.detail,
                    }
                    for c in financial_report.checks
                ],
            },
            "extracted_metrics": extracted_metrics,
            "red_flags": [
                {
                    "title": f.title,
                    "severity": f.severity,
                    "slide_number": f.slide_number,
                    "evidence_quote": f.evidence_quote,
                    "rule_violated": f.rule_violated,
                    "explanation": f.explanation,
                    "fix_suggestion": f.fix_suggestion,
                    "benchmark": f.benchmark,
                    "source_engine": f.source_engine,
                }
                for f in red_flags
            ],
            "feedback": {
                "executive_summary": feedback.executive_summary,
                "priority_actions": feedback.priority_actions,
                "hallucination_warnings": feedback.hallucination_warnings,
            },
            "metrics": {
                "total_red_flags": metrics.total_red_flags,
                "red_flags_with_citations": metrics.red_flags_with_citations,
                "citation_accuracy_rate": metrics.citation_accuracy_rate,
                "financial_checks_run": metrics.financial_checks_run,
                "financial_checks_with_findings": metrics.financial_checks_with_findings,
                "hallucinated_claims_detected": metrics.hallucinated_claims_detected,
                "weak_sections_count": metrics.weak_sections_count,
                "overall_confidence_score": metrics.overall_confidence_score,
            },
            "slide_map": slide_map,

            "bias": {
                "gender_detected": bias_report.gender_detected,
                "scoring_is_gender_neutral": bias_report.scoring_is_gender_neutral,
                "non_us_market": bias_report.non_us_market,
                "currency_detected": bias_report.currency_detected,
                "scoring_is_geography_neutral": bias_report.scoring_is_geography_neutral,
                "linguistic_complexity_score": bias_report.linguistic_complexity_score,
                "overall_bias_risk": bias_report.overall_bias_risk,
                "audit_summary": bias_report.audit_summary,
                "criteria_checked": bias_report.criteria_checked,
                "criteria_demographic_free": bias_report.criteria_demographic_free,
                "flags": [
                    {
                        "category": f.category,
                        "finding": f.finding,
                        "severity": f.severity,
                        "detail": f.detail,
                        "mitigation": f.mitigation,
                    }
                    for f in bias_report.bias_flags
                ],
            },
        }

        return JSONResponse(content=response)

    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected analysis error: {str(e)}\n{tb}"
        )
    finally:
        # Always clean up temp file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
