'''
"""
scoring_engine.py
Rule-based scoring for 8 pitch deck sections. No AI involved.
Each section scored 0-10 based on presence and quality of content signals.
"""

import re
from dataclasses import dataclass, field
from typing import Optional
from parser.pdf_parser import ParsedDeck


SECTION_WEIGHTS = {
    "Problem": 1.0,
    "Solution": 1.0,
    "Market Size": 1.0,
    "Business Model": 1.0,
    "Traction": 1.5,
    "Team": 1.0,
    "Financials": 1.5,
    "Ask": 1.0,
}


@dataclass
class SectionScore:
    section: str
    score: float               # 0-10
    max_score: float = 10.0
    weight: float = 1.0
    criteria_met: list[str] = field(default_factory=list)
    criteria_missed: list[str] = field(default_factory=list)
    slide_numbers: list[int] = field(default_factory=list)
    summary: str = ""


@dataclass
class ScoringReport:
    sections: list[SectionScore]
    overall_score: float
    weighted_score: float
    weakest_sections: list[str]
    strongest_sections: list[str]


def _get_section_text(deck: ParsedDeck, category: str) -> tuple[str, list[int]]:
    """Collect all text from slides assigned to a category."""
    text_parts = []
    slide_nums = []
    for slide in deck.slides:
        if slide.primary_category == category or slide.secondary_category == category:
            text_parts.append(slide.raw_text)
            slide_nums.append(slide.slide_number)
    return " ".join(text_parts).lower(), slide_nums


def _has(text: str, patterns: list[str]) -> bool:
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def score_problem(deck: ParsedDeck) -> SectionScore:
    text, slides = _get_section_text(deck, "Problem")
    # Also check full deck for problem signals
    full = deck.all_text.lower()

    criteria = {
        "Specific problem stated": _has(text + full, [r'\bproblem\b', r'\bpain\b', r'\bchallenge\b']),
        "Problem is quantified": _has(text + full, [r'\d+\s*%', r'\$[\d,]+', r'\d+\s+(?:million|billion|hours?|days?|companies)']),
        "Target customer mentioned": _has(text + full, [r'(?:small business|enterprise|startup|consumer|b2b|b2c|smb|founder|developer|doctor|patient)', r'target(?:ed)?\s+(?:customer|user|market|audience)']),
        "Market pain evidenced": _has(text + full, [r'currently|today|existing\s+solution|status quo|manual|legacy', r'inefficient|broken|expensive|slow|frustrating']),
    }

    score = sum(2.5 for v in criteria.values() if v)
    met = [k for k, v in criteria.items() if v]
    missed = [k for k, v in criteria.items() if not v]

    return SectionScore(
        section="Problem",
        score=round(score, 1),
        weight=SECTION_WEIGHTS["Problem"],
        criteria_met=met,
        criteria_missed=missed,
        slide_numbers=slides,
        summary=f"{'Strong' if score >= 7 else 'Moderate' if score >= 4 else 'Weak'} problem definition. {len(met)}/4 criteria met.",
    )


def score_solution(deck: ParsedDeck) -> SectionScore:
    text, slides = _get_section_text(deck, "Solution")
    full = deck.all_text.lower()

    criteria = {
        "Solution clearly described": _has(text + full, [r'platform|product|software|system|service|tool|app|api']),
        "Maps to the stated problem": _has(text + full, [r'solves?|addresses?|fixes?|eliminates?|reduces?|enables?']),
        "Differentiation mentioned": _has(text + full, [r'unique|proprietary|patent|unlike|vs\.?|competitor|differentiator|moat|advantage']),
        "How it works explained": _has(text + full, [r'how\s+it\s+works?|step|process|workflow|using|by\s+leveraging|powered by|built on']),
    }

    score = sum(2.5 for v in criteria.values() if v)
    met = [k for k, v in criteria.items() if v]
    missed = [k for k, v in criteria.items() if not v]

    return SectionScore(
        section="Solution",
        score=round(score, 1),
        weight=SECTION_WEIGHTS["Solution"],
        criteria_met=met,
        criteria_missed=missed,
        slide_numbers=slides,
        summary=f"{'Clear' if score >= 7 else 'Partial' if score >= 4 else 'Unclear'} solution presentation. {len(met)}/4 criteria met.",
    )


def score_market_size(deck: ParsedDeck) -> SectionScore:
    text, slides = _get_section_text(deck, "Market Size")
    full = deck.all_text.lower()

    criteria = {
        "TAM stated": _has(full, [r'\btam\b', r'total\s+addressable\s+market']),
        "SAM stated": _has(full, [r'\bsam\b', r'serviceable\s+addressable']),
        "SOM stated": _has(full, [r'\bsom\b', r'serviceable\s+obtainable']),
        "Sources cited": _has(full, [r'according to|source:|gartner|forrester|idc|statista|mckinsey|report|research|data from']),
        "Methodology explained": _has(full, [r'bottom.?up|top.?down|methodology|calculated|estimate|based on|assuming|penetration']),
    }

    score = sum(2.0 for v in criteria.values() if v)
    met = [k for k, v in criteria.items() if v]
    missed = [k for k, v in criteria.items() if not v]

    return SectionScore(
        section="Market Size",
        score=min(round(score, 1), 10.0),
        weight=SECTION_WEIGHTS["Market Size"],
        criteria_met=met,
        criteria_missed=missed,
        slide_numbers=slides,
        summary=f"{'Well-supported' if score >= 7 else 'Partial' if score >= 4 else 'Weak'} market sizing. {len(met)}/5 criteria met.",
    )


def score_business_model(deck: ParsedDeck) -> SectionScore:
    text, slides = _get_section_text(deck, "Business Model")
    full = deck.all_text.lower()

    criteria = {
        "Revenue model clear": _has(full, [r'subscription|saas|transaction\s+fee|licensing|per\s+seat|usage.based|freemium|marketplace\s+take']),
        "Pricing stated": _has(full, [r'price[ds]?\s+at|\$\d+\s+per|pricing|plan[s]?\s+start']),
        "Unit economics present": _has(full, [r'\bltv\b|\bcac\b|\barpu\b|\barppu\b|lifetime\s+value|customer\s+acquisition\s+cost|average\s+revenue\s+per']),
        "Path to revenue clear": _has(full, [r'customer[s]?\s+pay|generate\s+revenue|monetize|sell\s+to|charge']),
    }

    score = sum(2.5 for v in criteria.values() if v)
    met = [k for k, v in criteria.items() if v]
    missed = [k for k, v in criteria.items() if not v]

    return SectionScore(
        section="Business Model",
        score=round(score, 1),
        weight=SECTION_WEIGHTS["Business Model"],
        criteria_met=met,
        criteria_missed=missed,
        slide_numbers=slides,
        summary=f"{'Clear' if score >= 7 else 'Partial' if score >= 4 else 'Unclear'} business model. {len(met)}/4 criteria met.",
    )


def score_traction(deck: ParsedDeck) -> SectionScore:
    text, slides = _get_section_text(deck, "Traction")
    full = deck.all_text.lower()

    criteria = {
        "Metrics present (users/revenue)": _has(full, [r'\d+\s+(?:users?|customers?|clients?|subscribers?)', r'mrr|arr|\$\d+\s+revenue']),
        "Metrics are time-stamped": _has(full, [r'20\d{2}|q[1-4]\s+20\d{2}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec', r'last\s+(?:month|quarter|year)']),
        "Growth rate stated": _has(full, [r'\d+\s*%\s*(?:growth|increase|mom|yoy|qoq)', r'grew\s+(?:by\s+)?\d+']),
        "Customer names or logos mentioned": _has(full, [r'partners?\s+include|customers?\s+include|clients?\s+include|signed|contracted|logo']),
        "Retention or engagement metrics": _has(full, [r'retention|churn|nps|dau|mau|engagement|stickiness|repeat']),
    }

    score = sum(2.0 for v in criteria.values() if v)
    met = [k for k, v in criteria.items() if v]
    missed = [k for k, v in criteria.items() if not v]

    return SectionScore(
        section="Traction",
        score=min(round(score, 1), 10.0),
        weight=SECTION_WEIGHTS["Traction"],
        criteria_met=met,
        criteria_missed=missed,
        slide_numbers=slides,
        summary=f"{'Strong' if score >= 7 else 'Some' if score >= 4 else 'Limited'} traction evidence. {len(met)}/5 criteria met.",
    )


def score_team(deck: ParsedDeck) -> SectionScore:
    text, slides = _get_section_text(deck, "Team")
    full = deck.all_text.lower()

    criteria = {
        "Founders named": _has(full, [r'(?:ceo|cto|coo|co-founder|founder)[:\s]+[A-Z][a-z]', r'founded\s+by']),
        "Relevant backgrounds mentioned": _has(full, [r'previously\s+at|ex[-\s]|formerly\s+at|worked\s+at|background\s+in|experience\s+in']),
        "Domain expertise evident": _has(full, [r'years?\s+(?:of\s+)?experience|\d+\s*\+?\s*years?|expert|specialist|phd|professor|research']),
        "Advisors mentioned": _has(full, [r'\badvisor[s]?\b|\bboard\b|mentor|backed by']),
    }

    score = sum(2.5 for v in criteria.values() if v)
    met = [k for k, v in criteria.items() if v]
    missed = [k for k, v in criteria.items() if not v]

    return SectionScore(
        section="Team",
        score=round(score, 1),
        weight=SECTION_WEIGHTS["Team"],
        criteria_met=met,
        criteria_missed=missed,
        slide_numbers=slides,
        summary=f"{'Strong' if score >= 7 else 'Partial' if score >= 4 else 'Weak'} team presentation. {len(met)}/4 criteria met.",
    )


def score_financials(deck: ParsedDeck) -> SectionScore:
    text, slides = _get_section_text(deck, "Financials")
    full = deck.all_text.lower()

    criteria = {
        "Revenue projections present": _has(full, [r'(?:revenue|arr|mrr)\s+(?:projection|forecast)', r'projected\s+revenue', r'20\d{2}[^\d]*\$[\d,.]+']),
        "Burn rate stated": _has(full, [r'burn\s+rate|monthly\s+burn|cash\s+burn|\$[\d.]+[kmb]?\s+(?:per\s+month|\/month|monthly)']),
        "Runway stated": _has(full, [r'runway|months?\s+of\s+(?:cash|runway)']),
        "Path to profitability": _has(full, [r'profitab|break.?even|ebitda\s+positive|cash\s+flow\s+positive|profitable\s+by']),
        "Unit economics or margins": _has(full, [r'gross\s+margin|unit\s+economics|\bltv\b|\bcac\b|contribution\s+margin']),
    }

    score = sum(2.0 for v in criteria.values() if v)
    met = [k for k, v in criteria.items() if v]
    missed = [k for k, v in criteria.items() if not v]

    return SectionScore(
        section="Financials",
        score=min(round(score, 1), 10.0),
        weight=SECTION_WEIGHTS["Financials"],
        criteria_met=met,
        criteria_missed=missed,
        slide_numbers=slides,
        summary=f"{'Comprehensive' if score >= 7 else 'Partial' if score >= 4 else 'Incomplete'} financial picture. {len(met)}/5 criteria met.",
    )


def score_ask(deck: ParsedDeck) -> SectionScore:
    text, slides = _get_section_text(deck, "Ask")
    full = deck.all_text.lower()

    criteria = {
        "Raise amount stated": _has(full, [r'raising\s+\$|raise\s+\$|seeking\s+\$|round\s+(?:size\s+)?\$|\$[\d.]+[kmb]?\s+(?:seed|series|round)']),
        "Use of funds explained": _has(full, [r'use\s+of\s+funds?|use\s+of\s+proceeds|fund\s+allocation|breakdown\s+of']),
        "Valuation mentioned": _has(full, [r'valuation|pre.?money|post.?money']),
        "Milestone plan tied to raise": _has(full, [r'milestone|achieve|plan\s+to|will\s+use|enable\s+us|reach|goal\s+(?:is\s+to|by)']),
    }

    score = sum(2.5 for v in criteria.values() if v)
    met = [k for k, v in criteria.items() if v]
    missed = [k for k, v in criteria.items() if not v]

    return SectionScore(
        section="Ask",
        score=round(score, 1),
        weight=SECTION_WEIGHTS["Ask"],
        criteria_met=met,
        criteria_missed=missed,
        slide_numbers=slides,
        summary=f"{'Complete' if score >= 7 else 'Partial' if score >= 4 else 'Incomplete'} funding ask. {len(met)}/4 criteria met.",
    )


def run_scoring_engine(deck: ParsedDeck) -> ScoringReport:
    sections = [
        score_problem(deck),
        score_solution(deck),
        score_market_size(deck),
        score_business_model(deck),
        score_traction(deck),
        score_team(deck),
        score_financials(deck),
        score_ask(deck),
    ]

    # Weighted average
    weighted_sum = sum(s.score * s.weight for s in sections)
    weight_total = sum(s.weight for s in sections)
    weighted_score = weighted_sum / weight_total if weight_total else 0.0

    # Simple average for display
    overall_score = sum(s.score for s in sections) / len(sections)

    sorted_sections = sorted(sections, key=lambda s: s.score)
    weakest = [s.section for s in sorted_sections[:2]]
    strongest = [s.section for s in sorted_sections[-2:]]

    return ScoringReport(
        sections=sections,
        overall_score=round(overall_score, 1),
        weighted_score=round(weighted_score, 1),
        weakest_sections=weakest,
        strongest_sections=strongest,
    )
'''

"""
scoring_engine.py
Semantic scoring for 8 pitch deck sections using Cohere embeddings.
Criteria detection is meaning-based, not keyword-based.
No AI used for scoring decisions — all deterministic similarity thresholds.
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional
import cohere
from parser.pdf_parser import ParsedDeck

_cohere_client = None

def _get_cohere():
    global _cohere_client
    if _cohere_client is None:
        _cohere_client = cohere.Client(os.environ.get("COHERE_API_KEY"))
    return _cohere_client


SECTION_WEIGHTS = {
    "Problem": 1.0,
    "Solution": 1.0,
    "Market Size": 1.0,
    "Business Model": 1.0,
    "Traction": 1.5,
    "Team": 1.0,
    "Financials": 1.5,
    "Ask": 1.0,
}


@dataclass
class SectionScore:
    section: str
    score: float
    max_score: float = 10.0
    weight: float = 1.0
    criteria_met: list[str] = field(default_factory=list)
    criteria_missed: list[str] = field(default_factory=list)
    slide_numbers: list[int] = field(default_factory=list)
    summary: str = ""


@dataclass
class ScoringReport:
    sections: list[SectionScore]
    overall_score: float
    weighted_score: float
    weakest_sections: list[str]
    strongest_sections: list[str]


# ---------------------------------------------------------------------------
# Semantic criteria definitions
# Each criterion has a name and a list of reference sentences that describe
# what it looks like when the criterion IS met.
# ---------------------------------------------------------------------------

SECTION_CRITERIA = {
    "Problem": [
        ("Specific problem stated", [
            "There is a specific problem or pain point that customers experience",
            "The slide clearly identifies what is broken or frustrating for users",
            "A real challenge faced by a specific group of people is described",
        ]),
        ("Problem is quantified", [
            "The problem is backed by a number, statistic, or dollar amount",
            "Data shows how many people are affected or how much money is lost",
            "The scale of the problem is measured with specific figures",
        ]),
        ("Target customer mentioned", [
            "A specific type of customer, user, or business is identified as the target",
            "The slide mentions who exactly experiences this problem",
            "The affected group such as small businesses, developers, or consumers is named",
        ]),
        ("Market pain evidenced", [
            "The current situation is described as inefficient, expensive, or broken",
            "Existing solutions are shown to be inadequate or outdated",
            "The status quo is shown to be painful or costly for customers",
        ]),
    ],
    "Solution": [
        ("Solution clearly described", [
            "The product, platform, or service being built is clearly explained",
            "What the company has built and how it works is described",
            "The core features and capabilities of the solution are shown",
        ]),
        ("Maps to the stated problem", [
            "The solution directly addresses the problem mentioned earlier",
            "The product solves, reduces, or eliminates the identified pain point",
            "There is a clear connection between the problem and what was built",
        ]),
        ("Differentiation mentioned", [
            "The solution is described as unique, proprietary, or better than alternatives",
            "Competitive advantages or a defensible moat are mentioned",
            "The slide explains why this solution is different from what already exists",
        ]),
        ("How it works explained", [
            "The mechanism or process by which the product works is described",
            "Steps, workflow, or technology stack behind the solution is explained",
            "The product demo, screenshots, or architecture shows how it functions",
        ]),
    ],
    "Market Size": [
        ("TAM stated", [
            "The total addressable market size is stated in dollar terms",
            "The overall market opportunity is quantified with a large number",
            "We are going after a market worth billions of dollars globally",
        ]),
        ("SAM stated", [
            "The serviceable addressable market segment is defined",
            "The portion of the market the company can realistically reach is stated",
            "A subset of the total market that fits the product is quantified",
        ]),
        ("SOM stated", [
            "The serviceable obtainable market or target market share is defined",
            "The realistic near-term revenue opportunity is quantified",
            "The expected market capture in the first few years is stated",
        ]),
        ("Sources cited", [
            "Market size figures are backed by research reports or data sources",
            "Third party data from analysts or research firms is referenced",
            "The source of market size estimates is mentioned",
        ]),
        ("Methodology explained", [
            "The method used to calculate market size is explained",
            "Bottom-up or top-down analysis is used to arrive at the numbers",
            "Assumptions behind the market size estimate are disclosed",
        ]),
    ],
    "Business Model": [
        ("Revenue model clear", [
            "How the company generates revenue is clearly explained",
            "The company charges a subscription, commission, or licensing fee",
            "The monetization strategy and revenue streams are described",
        ]),
        ("Pricing stated", [
            "Specific pricing tiers, prices, or fee structures are mentioned",
            "How much customers pay and on what basis is stated",
            "The cost to the customer is shown with specific numbers",
        ]),
        ("Unit economics present", [
            "Customer acquisition cost and lifetime value are mentioned",
            "The economics per customer including LTV and CAC are shown",
            "Revenue per user or contribution margin is calculated",
        ]),
        ("Path to revenue clear", [
            "It is clear how and when the company will start generating revenue",
            "The path from product to paying customers is described",
            "The sales motion and how money flows into the business is explained",
        ]),
    ],
    "Traction": [
        ("Metrics present", [
            "Specific numbers showing user growth, revenue, or adoption are shown",
            "The company has paying customers or active users with numbers to prove it",
            "Key performance metrics like monthly recurring revenue or downloads are stated",
        ]),
        ("Metrics are time-stamped", [
            "Growth numbers are tied to specific dates, months, or quarters",
            "The timeline of growth is shown so trends can be evaluated",
            "Metrics are labeled with the time period they cover",
        ]),
        ("Growth rate stated", [
            "The rate of growth month over month or year over year is stated",
            "The company is growing at a specific percentage rate",
            "Growth velocity is shown with a percentage increase",
        ]),
        ("Customer names or logos", [
            "Specific customer names, logos, or company names are shown",
            "Notable clients or partners are identified by name",
            "Brand name customers or reference accounts are mentioned",
        ]),
        ("Retention or engagement", [
            "How often customers return, retention rate, or churn is mentioned",
            "User engagement, daily active users, or session frequency is shown",
            "Customers are sticking around and the retention data proves it",
        ]),
    ],
    "Team": [
        ("Founders named", [
            "The founders or co-founders are identified by name",
            "The CEO, CTO, or founding team members are introduced",
            "The people building the company are named and their roles stated",
        ]),
        ("Relevant backgrounds", [
            "The team previously worked at relevant companies or in the industry",
            "Prior experience at notable startups or large companies is mentioned",
            "Work history that is relevant to this startup is described",
        ]),
        ("Domain expertise evident", [
            "The team has deep expertise in the problem space",
            "Years of experience in the relevant field are mentioned",
            "Technical credentials, PhDs, or specialist knowledge is shown",
        ]),
        ("Advisors mentioned", [
            "Advisors, board members, or mentors supporting the company are named",
            "Notable investors or industry experts advising the team are mentioned",
            "The advisory board or strategic supporters are described",
        ]),
    ],
    "Financials": [
        ("Revenue projections present", [
            "Future revenue forecasts for the next few years are shown",
            "Projected annual recurring revenue or monthly revenue figures are stated",
            "A financial model showing expected growth is presented",
        ]),
        ("Burn rate stated", [
            "The monthly cash burn rate is mentioned",
            "How much money the company spends each month is stated",
            "Cash consumption rate and operating costs are disclosed",
        ]),
        ("Runway stated", [
            "How many months of runway the company has is stated",
            "The number of months until the company runs out of cash is shown",
            "Post-raise runway in months is mentioned",
        ]),
        ("Path to profitability", [
            "When the company expects to become profitable is stated",
            "The break-even point or path to positive cash flow is shown",
            "Financial milestones on the road to profitability are described",
        ]),
        ("Unit economics or margins", [
            "Gross margin, contribution margin, or unit profitability is stated",
            "The economics of each sale including cost and revenue are shown",
            "Margin structure and profitability per unit are described",
        ]),
    ],
    "Ask": [
        ("Raise amount stated", [
            "The amount of funding being raised is clearly stated",
            "The company is seeking a specific dollar amount from investors",
            "The round size in dollars is mentioned",
        ]),
        ("Use of funds explained", [
            "How the investment will be spent is explained",
            "The allocation of funds across hiring, product, and marketing is shown",
            "Where investor money will go is broken down",
        ]),
        ("Valuation mentioned", [
            "The pre-money or post-money valuation is stated",
            "The company valuation at which the round is being raised is mentioned",
            "Valuation cap or equity percentage being offered is described",
        ]),
        ("Milestone plan tied to raise", [
            "Specific milestones the raise will help achieve are described",
            "What the company will accomplish with this funding is explained",
            "Goals to be reached with investor capital are stated",
        ]),
    ],
}


def _semantic_check_criteria(full_text: str, criteria_list: list) -> dict[str, bool]:
    """
    For each criterion, embed the full section text and compare against
    reference sentences using cosine similarity.
    Returns dict of criterion_name -> bool (met or not).
    """
    if not full_text or len(full_text.strip()) < 15:
        return {name: False for name, _ in criteria_list}

    try:
        co = _get_cohere()

        # Collect all reference sentences
        all_refs = []
        ref_map = []  # (criterion_name, ref_index)
        for name, refs in criteria_list:
            for ref in refs:
                all_refs.append(ref)
                ref_map.append(name)

        # Embed reference sentences
        ref_response = co.embed(
            texts=all_refs,
            model="embed-english-v3.0",
            input_type="search_document",
        )
        ref_embeddings = ref_response.embeddings

        # Embed the section text
        text_response = co.embed(
            texts=[full_text[:3000]],
            model="embed-english-v3.0",
            input_type="search_query",
        )
        text_embedding = text_response.embeddings[0]

        # Compute best similarity per criterion
        criterion_sims: dict[str, list[float]] = {name: [] for name, _ in criteria_list}
        for ref_emb, crit_name in zip(ref_embeddings, ref_map):
            dot = sum(a * b for a, b in zip(text_embedding, ref_emb))
            norm_a = sum(x ** 2 for x in text_embedding) ** 0.5
            norm_b = sum(x ** 2 for x in ref_emb) ** 0.5
            sim = dot / (norm_a * norm_b) if norm_a and norm_b else 0.0
            criterion_sims[crit_name].append(sim)

        # Threshold: similarity > 0.45 means criterion is met
        results = {}
        for name, sims in criterion_sims.items():
            best = max(sims) if sims else 0.0
            results[name] = best > 0.38

        return results

    except Exception:
        # Fallback: all false
        return {name: False for name, _ in criteria_list}


def _get_section_text(deck: ParsedDeck, category: str) -> tuple[str, list[int]]:
    """Collect all text from slides semantically assigned to a category."""
    text_parts = []
    slide_nums = []

    # Primary match
    for slide in deck.slides:
        if slide.primary_category == category or slide.secondary_category == category:
            text_parts.append(slide.raw_text)
            slide_nums.append(slide.slide_number)

    # If no slides matched, use top-3 slides by category score
    if not text_parts:
        scored = sorted(deck.slides, key=lambda s: s.category_scores.get(category, 0), reverse=True)
        for slide in scored[:3]:
            if slide.category_scores.get(category, 0) > 1.0:
                text_parts.append(slide.raw_text)
                slide_nums.append(slide.slide_number)

    return " ".join(text_parts), slide_nums


def _score_section(deck: ParsedDeck, section: str) -> SectionScore:
    criteria_list = SECTION_CRITERIA[section]
    n = len(criteria_list)
    points_each = 10.0 / n

    text, slides = _get_section_text(deck, section)

    # Also pull relevant text from full deck for sections that may be spread out
    full_text = text + " " + deck.all_text[:4000]

    results = _semantic_check_criteria(full_text, criteria_list)

    met = [name for name, passed in results.items() if passed]
    missed = [name for name, passed in results.items() if not passed]
    score = round(len(met) * points_each, 1)

    quality = "Strong" if score >= 7 else "Partial" if score >= 4 else "Weak"
    summary = f"{quality} {section.lower()} coverage. {len(met)}/{n} criteria met."

    return SectionScore(
        section=section,
        score=min(score, 10.0),
        weight=SECTION_WEIGHTS[section],
        criteria_met=met,
        criteria_missed=missed,
        slide_numbers=slides,
        summary=summary,
    )


def run_scoring_engine(deck: ParsedDeck) -> ScoringReport:
    sections = []
    for section in SECTION_CRITERIA:
        sections.append(_score_section(deck, section))

    weighted_sum = sum(s.score * s.weight for s in sections)
    weight_total = sum(s.weight for s in sections)
    weighted_score = weighted_sum / weight_total if weight_total else 0.0
    overall_score = sum(s.score for s in sections) / len(sections)

    sorted_sections = sorted(sections, key=lambda s: s.score)
    weakest = [s.section for s in sorted_sections[:2]]
    strongest = [s.section for s in sorted_sections[-2:]]

    return ScoringReport(
        sections=sections,
        overall_score=round(overall_score, 1),
        weighted_score=round(weighted_score, 1),
        weakest_sections=weakest,
        strongest_sections=strongest,
    )