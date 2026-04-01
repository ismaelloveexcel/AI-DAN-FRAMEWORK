# Airtable Setup — AIDAN Tracker

Step-by-step setup. Takes 10–15 minutes. Do this once.

---

## Step 1: Create Airtable Account

1. Go to [airtable.com](https://airtable.com)
2. Sign up with your email (free plan is enough)
3. No credit card needed

---

## Step 2: Create the Base

1. Click **+ Add a base**
2. Choose **Start from scratch**
3. Name it: `AIDAN Tracker`
4. Click **Create base**

---

## Step 3: Create Table 1 — Products

Rename the default table to `Products`.

Add these fields exactly (delete any default fields first):

| Field Name | Field Type | Notes |
|---|---|---|
| Product | Single line text | Primary field — product name |
| Status | Single select | Options: Idea, Validating, Building, Live, Killed |
| Revenue_MRR | Currency | Currency: MUR (Mauritius Rupee) — if MUR is unavailable, use Number field type with Rs prefix in the field name |
| Users | Number | Total signups/users |
| Paying_Users | Number | Users who have paid |
| Week | Date | Week of the entry |
| Notes | Long text | What's working, what's failing |
| Stage | Single select | Options: Idea, Validate, Build, Launch, Revenue, Improve |

**To add a Single Select option:**
1. Click on the field header
2. Select "Single select"
3. Click "+ Add an option" for each value above

---

## Step 4: Pre-populate Products Table

Add these 3 rows now:

| Product | Status | Stage | Notes |
|---|---|---|---|
| CareerScore MU | Building | Build | AI CV scoring for Mauritius job seekers |
| AI Excel Report Generator | Idea | Idea | Upload spreadsheet → clean report |
| Small Business AI Assistant | Idea | Idea | WhatsApp chatbot for Mauritius SMBs |

---

## Step 5: Create Table 2 — CV Submissions

Click **+ Add a table** and name it `CV Submissions`.

Add these fields:

| Field Name | Field Type | Notes |
|---|---|---|
| Name | Single line text | Primary field |
| Email | Email | User's email |
| Target_Role | Single line text | What role they're targeting |
| CV_Score | Number | The score AIDAN gave them (0–100) |
| Date | Date | Date they submitted |
| Paid_Upgrade | Checkbox | Did they pay for anything? |
| Upgrade_Type | Single select | Options: Job Feed, CV Rewrite, Interview Coaching, None |
| Notes | Long text | Any manual notes |

---

## Step 6: Create Views

### In the Products table:

**View 1: Active Products**
1. Click **+ Add view** → Grid view
2. Name it `Active Products`
3. Filter: Status is not "Killed"

**View 2: Revenue Dashboard**
1. Click **+ Add view** → Gallery view (or Grid)
2. Name it `Revenue Dashboard`
3. Sort by: Revenue_MRR (descending)
4. Show fields: Product, Revenue_MRR, Users, Paying_Users, Status

**View 3: This Week**
1. Click **+ Add view** → Grid view
2. Name it `This Week`
3. Filter: Week = "is within" → "this week"

### In the CV Submissions table:

**View 1: All Submissions**
- Default grid view (rename to `All Submissions`)

**View 2: Paid Subscribers**
1. Click **+ Add view** → Grid view
2. Name it `Paid Subscribers`
3. Filter: Paid_Upgrade = Checked

---

## Step 7: Connect to the API (Optional — for automation)

When ready to automate CV submission capture:

1. Go to your Airtable account → **API**
2. Find your `Personal access token` (Settings → Developer hub)
3. Your `Base ID` is in the URL: `airtable.com/YOUR_BASE_ID/...`
4. Add both to your `config/.env.example`:
   ```
   AIRTABLE_API_KEY=your-token-here
   AIRTABLE_BASE_ID=your-base-id-here
   ```
5. The landing page's TODO comment shows exactly how to POST to Airtable

---

## Weekly Ritual (Every Sunday, 30 min)

1. Open AIDAN Tracker
2. Update `Revenue_MRR` for CareerScore MU
3. Update `Users` and `Paying_Users`
4. Write one sentence in `Notes` about what happened this week
5. Set `Week` to today's date
6. Close Airtable

That's it. This is your single source of truth.
