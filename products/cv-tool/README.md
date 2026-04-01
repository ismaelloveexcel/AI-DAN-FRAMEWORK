# CareerScore MU — AI-Powered CV Scoring for Mauritius

## One-Liner
AI-powered CV scoring for Mauritius job seekers. Upload your CV, get an instant score, gap analysis, matching jobs, and salary benchmark — specific to the Mauritius market.

---

## Product Brief

### Target User
- Age: 20s–30s
- Location: Mauritius (primary), Mauritian diaspora (secondary)
- Situation: Job seekers who are applying but not getting interviews
- Pain: "I don't know why I'm not getting called back"

### The Problem
Mauritius job seekers submit dozens of CVs and hear nothing back. They don't know:
- Why their CV is being rejected
- What skills are missing for their target role
- What salary they should be asking for
- Which companies are actually hiring

Generic CV tools (like CV.com or Zety) don't understand the Mauritius job market — local industries, salary benchmarks, or company names.

### The Solution
Upload your CV → get instant AI-powered:
1. **Score (0–100%)** — How competitive is your CV for your target role?
2. **Gap Analysis** — What's missing vs. what employers actually want?
3. **Matching Jobs** — 3–4 real job types with salary ranges in Rs
4. **Salary Benchmark** — What should you be earning based on role + experience?
5. **Skills to Add** — The specific skills that will move your score up
6. **Free Courses** — HubSpot Academy, Coursera, YouTube links to close the gaps fast

---

## Pricing Model

### FREE Tier
- CV Score (0–100%)
- Bullet-point gap list (top 5 gaps)
- 3–4 matching job types with salary range in Rs
- Missing skills list
- Free course suggestions (links included)
- **Goal:** Get users hooked, build email list

### Rs 500–1,500 — Full CV Rewrite
- Complete ATS-optimized CV rewrite
- Localized for Mauritius market
- Formatted for local companies
- 2-day turnaround

### Rs 200–500/month — Weekly Job Feed (RECURRING ← THIS IS MRR)
- Weekly curated job listings matched to their CV
- Sourced from LinkedIn, MyJob.mu, and Facebook groups
- Sent by email every Monday morning
- **45 subscribers at Rs 500/mo = $500 MRR target**

### Rs 1,000–3,000 — Interview Coaching
- 60-minute mock interview session
- Role-specific questions for Mauritius companies
- Written feedback report
- One-time purchase

### Commission Track
- Referrals to local training providers (coding bootcamps, IT certs, etc.)
- 10–20% commission per enrollment

---

## Revenue Math

To hit $500 MRR (≈ Rs 25,000/month):

| Revenue Stream | Price | Needed |
|---|---|---|
| Weekly Job Feed | Rs 500/mo | 50 subscribers |
| Weekly Job Feed | Rs 300/mo | 83 subscribers |
| Mix of tiers | Various | ~45 paying users |

**Realistic path:** 45 subscribers × Rs 500/mo = Rs 22,500/mo ≈ $490 MRR. Add 2–3 CV rewrites and you're there.

---

## $500 MRR Timeline

- **Week 1:** Build landing page + CV scoring prompt (Cursor)
- **Week 2:** Launch on Reddit r/mauritius + Facebook job groups
- **Week 3:** First 10 free users → convert 2–3 to paid job feed
- **Week 4–8:** Grow to 20 subscribers via word of mouth
- **Week 8–12:** Hit 45+ subscribers = $500 MRR

---

## Competitive Landscape

- **MyJob.mu** — job listings only, no CV analysis
- **CV.com / Zety** — generic, no Mauritius data
- **LinkedIn** — Premium CV analysis but expensive and not Mauritius-specific
- **Local recruiters** — manual, expensive, not scalable

**Gap:** Zero tools doing AI CV scoring specifically for the Mauritius job market.

---

## Tech Stack

- **CV input:** Paste text or upload (text extraction)
- **Scoring engine:** GPT-4o (via OpenAI API) using `scoring_prompt.md`
- **Salary data:** `salary_table.csv` (embedded in prompt context)
- **Skills data:** `skills_matrix.csv` (embedded in prompt context)
- **Frontend:** Static HTML (Vercel deployment) — see `landing_page.html`
- **Email capture:** Airtable form or Typeform (free tier)
- **Payments:** Stripe (Rs-denominated) or bank transfer initially
- **Job feed delivery:** Gmail or Resend (free tier)

---

## Launch Channels

See `launch_posts.md` for ready-to-use copy.

1. **Reddit** — r/mauritius, r/jobsearch
2. **Facebook** — Mauritius job groups (Jobs in Mauritius, etc.)
3. **LinkedIn** — Direct posts targeting Mauritius professionals
4. **WhatsApp** — Personal network (ask 5 people to share)

---

## Status

**Current Stage:** Building

**Done:**
- [ ] CV scoring prompt written
- [ ] Salary table populated
- [ ] Skills matrix populated
- [ ] Landing page built
- [ ] Landing page live on Vercel
- [ ] First 10 beta users
- [ ] First paying subscriber
