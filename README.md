# FlowState — AI Pitch Deck Analyzer

> Upload a pitch deck. Get a structured score, financial analysis, bias audit, and AI-generated narrative feedback in under 30 seconds.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Vite + Tailwind CSS |
| Backend | Python + FastAPI |
| AI — Narrative Feedback | Groq (`llama-3.3-70b-versatile`) |
| Semantic Analysis | Cohere (embeddings) |
| Scoring / Financials / Red Flags | Deterministic rule-based engines |
| PDF Parsing | pdfplumber + PyPDF2 |

---

## Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **Groq API key** — free at [console.groq.com](https://console.groq.com)
- **Cohere API key** — free at [dashboard.cohere.com](https://dashboard.cohere.com)

---

## First-Time Setup

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd flowstate
```

### 2. Add your API keys

Create a `.env` file inside the `backend/` folder:

```
GROQ_API_KEY=your_groq_key_here
COHERE_API_KEY=your_cohere_key_here
```

### 3. Install dependencies

**Backend:**
```bash
cd backend
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

### 4. Make the run script executable (one-time only)

```bash
chmod +x run.sh
```

---

## Running the App

```bash
./run.sh
```

Starts both backend (port 8000) and frontend (port 5173). Then open **http://localhost:5173**.

---

## Project Structure

```
flowstate/
├── backend/
│   ├── main.py                        # FastAPI entry point — /analyze endpoint
│   ├── requirements.txt
│   ├── .env                           # Your API keys (never commit this)
│   ├── parser/
│   │   ├── pdf_parser.py              # Extracts text and structure from PDF
│   │   └── deck_validator.py          # Validates deck is a pitch deck (5–60 slides)
│   ├── engine/
│   │   ├── scoring_engine.py          # Rule-based section scoring (Problem, Team, etc.)
│   │   ├── financial_engine.py        # Deterministic financial checks
│   │   └── red_flag_engine.py         # Flags critical issues with citations
│   ├── ai/
│   │   └── feedback_generator.py      # Groq/Llama — narrative text only
│   └── evaluation/
│       ├── bias_checker.py            # Gender, geographic, linguistic bias audit
│       └── metrics_tracker.py         # Session-level accuracy metrics
├── frontend/
│   └── src/
│       ├── App.jsx
│       └── components/
│           ├── UploadZone.jsx
│           ├── ScoreCard.jsx
│           ├── RedFlagList.jsx
│           ├── SlideMap.jsx
│           ├── BiasPanel.jsx
│           └── MetricsSidebar.jsx
├── run.sh                             # Starts backend + frontend together
└── README.md
```

---

## How It Works

1. **Upload** a PDF pitch deck (5–60 slides)
2. **Validator** confirms it's a pitch deck, not a random PDF
3. **Parser** extracts text and categorizes each slide
4. **Scoring engine** evaluates 8 sections (Problem, Solution, Market Size, Business Model, Traction, Team, Financials, Ask) against content criteria — fully deterministic
5. **Financial engine** runs rule-based checks on revenue, burn rate, margins, runway, and more
6. **Red flag engine** cross-references scoring and financial results to surface critical issues with slide citations
7. **Bias checker** audits for gender, geographic, and linguistic signals — confirms scoring stayed demographic-neutral throughout
8. **Groq (Llama)** generates the written narrative feedback based on the structured output above — AI touches nothing else
9. **Hallucination checker** validates the AI didn't invent numbers not present in the source data

> Scoring, red flags, and financials are 100% deterministic. The same deck always gets the same score. AI is only used to turn the structured output into readable prose.

---

## API

**`POST /analyze`** — Upload a pitch deck PDF

Returns: overall score, section scores, financial check results, red flags with slide citations, AI narrative, bias audit, and a slide-by-slide map.

**`GET /health`** — Health check

---

## Notes

- Only PDF files accepted, 5–60 slides
- `.env` is gitignored — never commit your API keys
- Analysis takes 15–30 seconds depending on deck size
- Financial benchmarks are calibrated for USD; non-USD decks will still work but currency flags will appear in the bias report