cat > README.md << 'EOF'
# 🦩 Pelican Risk

**NAICS classification and portfolio intelligence for Louisiana community banks, credit unions, and insurance agencies.**

Pelican Risk solves a specific problem: small financial institutions need accurate, documented, audit-ready business classification — but enterprise tools like Verisk, Guidewire, and Middesk are built and priced for national carriers and large banks. Pelican Risk is built for the institutions they ignore.

---

## What It Does

**Layer 1 — Classification Engine**
Submit a business name and address, get back a NAICS code, a real confidence score (0.0–1.0), conflict detection, and a human-readable reasoning statement. Every classification is stored permanently with a full audit trail.

**Layer 2 — Portfolio Intelligence**
Upload your entire commercial loan book or policy book as a CSV. Get back a concentration dashboard showing industry exposure by sector, with automatic warnings for any sector exceeding 20% of the portfolio.

**Layer 3 — Compliance-Ready Audit Trail**
Every classification has a documented rationale, timestamp, confidence score, and human sign-off step. When an examiner asks "why did you classify this business this way," the answer is a clean, exportable record — not "we asked an AI."

---

## Why Not Just Use ChatGPT?

A general-purpose AI can guess a NAICS code. It cannot:
- Store a persistent, queryable history of every classification decision
- Flag conflicts when a business name matches multiple industry codes
- Provide a documented rationale an examiner can review
- Show portfolio-level concentration risk across an entire loan book
- Lock a classification at 1.0 confidence after human review

Pelican Risk is not smarter than a chatbot. It is **consistent, documented, and workflow-ready** — which is what a compliance officer actually needs.

---

## Target Users

- Community banks and credit unions in Louisiana with $200M–$2B in assets
- Independent commercial lines insurance agencies writing oilfield, marine, or construction books
- Any institution currently classifying businesses manually in Excel

---

## Tech Stack

- **FastAPI** — REST API backend
- **SQLAlchemy + SQLite** — persistent database (swap to Postgres for production)
- **Streamlit** — frontend UI
- **Python 3.12**

---

## Getting Started

**1. Clone the repo**
```bash
git clone https://github.com/akrinsky99-jpg/pelican-risk
cd pelican-risk
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Start the API**
```bash
python -m uvicorn app.main:app --reload
```

The API runs on `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

On first startup the database initializes automatically and creates a demo customer. Get your API key:
```bash
python -c "from app.database import SessionLocal, Customer; db = SessionLocal(); print(db.query(Customer).first().api_key)"
```

**4. Start the frontend (in a second terminal)**
```bash
streamlit run frontend.py
```

The UI runs on `http://localhost:8501`. Paste your API key in the sidebar.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/classify` | Classify a single business |
| POST | `/classify/batch` | Classify up to 500 businesses from a list |
| PUT | `/classifications/{id}/confirm` | Human confirms a classification as correct |
| PUT | `/classifications/{id}/correct` | Human corrects a classification to a different code |
| GET | `/history` | Classification history, filterable by review status |
| GET | `/audit/{id}` | Full audit trail for a single classification |
| GET | `/portfolio/concentration` | Portfolio sector breakdown with concentration warnings |
| GET | `/health` | API health check |

All endpoints require an `x-api-key` header.

---

## Confidence Scoring

Pelican Risk uses a real 0.0–1.0 confidence score, not a string label.

| Score | Tier | Action |
|-------|------|--------|
| 0.85–1.00 | HIGH | Auto-confirmed, no review needed |
| 0.60–0.84 | MEDIUM | Recommended for human review |
| 0.00–0.59 | LOW | Required human review |
| 1.00 (locked) | CONFIRMED | Human-reviewed and signed off |

Scores are calculated based on keyword specificity, multi-keyword agreement, and conflict detection. When multiple keywords match but point to different NAICS codes, the system detects the conflict, lowers confidence, and flags the classification for mandatory review.

---

## Project Structure
pelican-risk/
├── app/
│   ├── __init__.py
│   ├── classifier.py
│   ├── confidence.py
│   ├── database.py
│   └── main.py
├── frontend.py
├── pelican_risk.db
├── README.md
└── requirements.txt

---

## Roadmap

- [ ] LLM fallback for businesses that don't match any keyword
- [ ] CSV export of audit trail for exam preparation
- [ ] Multi-user auth with role-based access (analyst vs. reviewer)
- [ ] Postgres support for production deployment
- [ ] Louisiana Secretary of State data integration for business verification
- [ ] CRA/Section 1071 reporting export

---

## Built By

Amanda K. — Information Systems & Analytics, LSU  
Baton Rouge, Louisiana
EOF