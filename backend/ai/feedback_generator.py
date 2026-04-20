"""
feedback_generator.py
AI is used ONLY here, and ONLY for natural language generation.
AI never evaluates numbers or finds red flags — that is done by the engines.
Uses Groq API with llama-3.3-70b-versatile model.
"""

import os
import re
import json
from groq import Groq
from dataclasses import dataclass, field
from engine.financial_engine import FinancialReport
from engine.scoring_engine import ScoringReport
from engine.red_flag_engine import RedFlag


@dataclass
class FeedbackOutput:
    executive_summary: str
    section_narratives: dict[str, str]
    priority_actions: list[str]
    hallucination_warnings: list[str]


def _build_system_prompt() -> str:
    return """You are a senior venture capital analyst with 15 years of experience evaluating pitch decks at the seed and Series A stage.

CRITICAL RULES — FOLLOW WITHOUT EXCEPTION:
1. You will be given a structured analysis report produced by a deterministic financial engine. Only reference data explicitly provided to you.
2. Do NOT invent, estimate, or fabricate any numbers, percentages, company names, or financial figures. Every specific claim must cite the slide number where evidence was found.
3. You are ONLY generating readable narrative text. All scoring, red flag identification, and financial checking has already been done.
4. When referencing a red flag or metric, cite the slide number using this format: (Slide N).
5. Write as a real investor giving honest, direct, respectful feedback. Be specific. Do not pad with generic encouragement.
6. Tone should be professional but candid.

OUTPUT FORMAT — RESPOND IN VALID JSON ONLY, no markdown, no code fences:
{
  "executive_summary": "3 sentences summarizing the deck overall strength and readiness.",
  "section_narratives": {
    "Problem": "One paragraph of investor-grade narrative feedback.",
    "Solution": "...",
    "Market Size": "...",
    "Business Model": "...",
    "Traction": "...",
    "Team": "...",
    "Financials": "...",
    "Ask": "..."
  },
  "priority_actions": [
    "Top priority fix with specific actionable instruction.",
    "Second priority fix.",
    "Third priority fix."
  ]
}"""


def _build_user_prompt(financial_report, scoring_report, red_flags):
    section_lines = []
    for s in scoring_report.sections:
        criteria_met = ", ".join(s.criteria_met) if s.criteria_met else "none"
        criteria_missed = ", ".join(s.criteria_missed) if s.criteria_missed else "none"
        section_lines.append(
            f"  - {s.section}: {s.score}/10 | Slides: {s.slide_numbers} | Met: [{criteria_met}] | Missing: [{criteria_missed}]"
        )

    check_lines = []
    for c in financial_report.checks:
        if c.result in ("warn", "fail"):
            check_lines.append(
                f"  - [{c.result.upper()}] {c.check_name} | Slide: {c.slide_number} | Evidence: {c.evidence_text or 'N/A'} | Rule: {c.rule_applied}"
            )

    flag_lines = []
    for f in red_flags[:10]:
        flag_lines.append(
            f"  - [{f.severity}] {f.title} | Slide: {f.slide_number} | Evidence: {f.evidence_quote or 'N/A'}"
        )

    prompt = f"""Here is the structured analysis report for a pitch deck. Generate narrative investor feedback based ONLY on the data below.

SECTION SCORES (rule-based, already computed):
{chr(10).join(section_lines)}

OVERALL WEIGHTED SCORE: {scoring_report.weighted_score}/10
WEAKEST SECTIONS: {', '.join(scoring_report.weakest_sections)}
STRONGEST SECTIONS: {', '.join(scoring_report.strongest_sections)}

FINANCIAL CHECK FINDINGS (deterministic rule-based results):
{chr(10).join(check_lines) if check_lines else '  - No financial warnings or failures detected.'}

FINANCIAL SUMMARY: {financial_report.summary}

RED FLAGS (already identified by rule engine):
{chr(10).join(flag_lines) if flag_lines else '  - No red flags identified.'}

Remember: Only reference data from above. Cite slide numbers. Do not invent numbers. Respond in valid JSON only, no markdown fences."""

    return prompt


def _extract_numbers_from_text(text):
    return re.findall(r'\b\d[\d,./]*%?\b', text)


def _check_hallucinations(ai_output, financial_report, scoring_report):
    source_numbers = set()
    for check in financial_report.checks:
        if check.evidence_text:
            source_numbers.update(_extract_numbers_from_text(check.evidence_text))
    for section in scoring_report.sections:
        source_numbers.add(str(section.score))
        source_numbers.add(str(int(section.score)))
    source_numbers.add(str(scoring_report.weighted_score))
    source_numbers.add(str(scoring_report.overall_score))
    for i in range(1, 65):
        source_numbers.add(str(i))

    warnings = []
    all_ai_text = (
        ai_output.executive_summary
        + " ".join(ai_output.section_narratives.values())
        + " ".join(ai_output.priority_actions)
    )
    ai_numbers = _extract_numbers_from_text(all_ai_text)

    for num in ai_numbers:
        clean = num.replace(",", "").replace("%", "").strip()
        if clean and clean not in source_numbers and len(clean) > 1:
            try:
                v = float(clean)
                if v > 100 and clean not in source_numbers:
                    warnings.append(f"Potential hallucination: '{num}' not found in source deck data")
            except ValueError:
                pass

    return list(set(warnings))


def generate_feedback(financial_report, scoring_report, red_flags):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set.")

    client = Groq(api_key=api_key)
    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(financial_report, scoring_report, red_flags)

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=4096,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw_text = response.choices[0].message.content.strip()
        raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
        raw_text = re.sub(r'\s*```$', '', raw_text)

        data = json.loads(raw_text)

        output = FeedbackOutput(
            executive_summary=data.get("executive_summary", ""),
            section_narratives=data.get("section_narratives", {}),
            priority_actions=data.get("priority_actions", []),
            hallucination_warnings=[],
        )
        output.hallucination_warnings = _check_hallucinations(output, financial_report, scoring_report)
        return output

    except json.JSONDecodeError as e:
        return FeedbackOutput(
            executive_summary=f"AI feedback parsing error: {str(e)}. Scores and red flags below are still accurate.",
            section_narratives={s.section: f"Score: {s.score}/10. {s.summary}" for s in scoring_report.sections},
            priority_actions=[f"Address the {f.title} issue." for f in red_flags[:3]],
            hallucination_warnings=["AI output could not be parsed as JSON."],
        )
    except Exception as e:
        return FeedbackOutput(
            executive_summary=f"AI feedback generation failed: {str(e)}. All scores and red flags are still valid.",
            section_narratives={s.section: s.summary for s in scoring_report.sections},
            priority_actions=[f"Fix {f.title}" for f in red_flags[:3]],
            hallucination_warnings=[f"AI generation error: {str(e)}"],
        )
