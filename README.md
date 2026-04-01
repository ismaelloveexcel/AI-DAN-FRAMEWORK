# AIDAN-OS — AI Daily Autonomous Navigator

**Solo operator business OS. One product → $500 MRR → Scale.**

AIDAN is your operator, not a tool. It gives you ONE task per day, keeps you focused, validates ideas before you build them, and tracks your path to $500 MRR — while making sure you don't burn out doing it.

> "This idea looks exciting… but it won't make money. Let's fix that before we waste 3 days."

---

## Quick Start (3 Steps)

```bash
# 1. Clone the repo
git clone https://github.com/ismaelloveexcel/AI-DAN-FRAMEWORK.git
cd AI-DAN-FRAMEWORK

# 2. Open the Mission Control dashboard (no server needed)
open dashboard/index.html

# 3. Follow today's task in the Today tab
```

**To run the API server (optional):**
```bash
pip install -r requirements.txt
cp config/.env.example .env  # add your OpenAI key
python api_server.py
# → http://localhost:8000/health
```

---

## Architecture

```
You → talk to AIDAN

AIDAN:
  → gives 1 task per day
  → validates ideas (5 Kill Criteria)
  → generates Cursor build prompts
  → tracks revenue
  → flags overwork

You:
  → approve or reject
  → execute the ONE task
  → track in Airtable
```

**The 4 functions (everything else is noise):**

| Function | What it does | Who handles |
|---|---|---|
| Find Ideas | Identify opportunities | AIDAN |
| Build Product | Create MVP fast | AIDAN + Cursor |
| Get Users | Organic traffic | AIDAN |
| Track Money | Revenue + metrics | Airtable |

---

## Current Products

| Product | Stage | Target MRR |
|---|---|---|
| CareerScore MU | Building | Rs 25,000/mo ($500) |
| AI Excel Report Generator | Idea | After CV Tool hits $500 |
| SMB AI Assistant | Idea | After CV Tool hits $500 |

**Rule: ONE product at a time until $500 MRR.**

---

## Repository Structure

```
AIDAN-OS/
├── aidan/               # AIDAN system prompt, pipeline, approval gates
├── products/
│   ├── cv-tool/         # Full product brief, scoring prompt, salary data, landing page
│   ├── excel-report-tool/
│   └── smb-assistant/
├── dashboard/           # index.html — Mission Control (offline, localStorage)
├── tracker/             # Airtable setup instructions
├── api/                 # Lean FastAPI server (6 endpoints)
├── config/              # .env.example
├── core/                # config, llm, exceptions, http_client
├── agents/              # executive_chat
├── DAILY_PLAYBOOK.md    # Open every morning
└── requirements.txt     # ~10 dependencies
```

---

## Tech Stack

| Tool | Purpose |
|---|---|
| **Cursor** | Build apps fast |
| **ChatGPT** | AIDAN brain (paste system prompt) |
| **GitHub** | Code storage |
| **Airtable** | Revenue + user tracking |
| **Vercel** | Deploy static sites free |

No n8n. No CrewAI. No LangChain. No overengineering.

---

## The Rules

```
Revenue > Features
Execution > Planning
Speed > Perfection
Consistency > Intensity
$500 MRR > Everything else
```

---

## API Endpoints (6 only)

| Method | Endpoint | What it does |
|---|---|---|
| GET | /health | Health check |
| POST | /aidan/chat | Talk to AIDAN |
| POST | /aidan/daily | Get today's ONE task |
| POST | /aidan/evaluate | Evaluate an idea (5 Kill Criteria) |
| POST | /aidan/build-prompt | Generate Cursor-ready build prompt |
| POST | /aidan/weekly-review | Weekly what-worked / what-failed review |

---

## First Product: CareerScore MU

AI-powered CV scoring for Mauritius job seekers.

- Upload CV → get instant score (0-100%), gap analysis, salary benchmark, matching jobs
- Free tier (score + gaps) → paid job feed (Rs 500/mo)
- **45 subscribers = $500 MRR**
- No competitor doing AI CV scoring for Mauritius

See `products/cv-tool/` for full product brief, scoring prompt, salary data, and launch posts.

---

## After $500 MRR

Only then: add second product, start newsletter, add analytics, consider a contractor.

Not before.

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

*Built for solo operators who are serious about revenue, not frameworks.*
