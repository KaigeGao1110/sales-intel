# Scout — Sales Intelligence Platform
**Product Manual for Small Business Owners**

---

## What is Scout?

Scout monitors your target companies every day and tells you **when to reach out and what to say**. No more guessing, no more hours of manual research.

> Instead of spending 2 hours researching a company before a cold email, Scout does it in 30 seconds — and writes the email for you.

---

## Who is it for?

- **Solo founders** selling B2B products or services
- **Small sales teams** (1–5 people) without dedicated SDRs
- **Consultants, agencies, and freelancers** who need to research prospects fast

If your budget is tight and your time is tighter, Scout is built for you.

---

## The Three Problems Scout Solves

| Problem | Without Scout | With Scout |
|---------|--------------|------------|
| **Who to contact** | Gut feeling or random list | Ranked priority list updated daily |
| **When to contact** | Random intervals | Triggered by real signals (funding, hiring, layoffs) |
| **What to say** | Generic "I'd love to connect" | Personalized email based on their actual situation |

---

## Getting Started in 5 Minutes

### Step 1: Set your target customer profile (3 minutes)

Open `config/icp.json` and fill in your ideal customer:

```json
{
  "description": "SaaS companies, Series A-B, 50-200 employees",
  "min_employees": 50,
  "max_employees": 200,
  "industries": ["saas", "fintech", "software"],
  "funding_stages": ["Series A", "Series B"]
}
```

This tells Scout what a "good fit" looks like. Without this, Scout still works — but the priority ranking is smarter with it.

---

### Step 2: Add your first company (1 minute)

```bash
python main.py scout "Acme Corp" --domain acme.com
```

You'll get:
- A full company brief (what's happening, what they might need)
- The company is added to your monitoring list automatically

---

### Step 3: Generate an outreach email (1 minute)

```bash
python main.py outreach "Acme Corp"
```

You'll get:
- 2 email variants (pick one, edit slightly, send)
- 2 LinkedIn message variants
- Subject line options
- Personalized by the contact's name and role

That's it. From idea to sendable email in under 60 seconds.

---

## Your Daily Workflow

### Every morning (2 minutes)

```bash
# See which companies deserve attention today
python main.py rank
```

Scout shows you a ranked list of all your monitored companies:

```
Rank  Company     Score  Grade  Signal              Action
1     Acme Corp   87     A      New funding + hiring Reach out this week
2     Notion      62     B      Review rating drop  Follow up in 3 days
3     Slack       20     D      No clear signal     Hold off
```

**Only talk to A and B grade companies.** C and D go on the back burner.

---

### When you see an alert (30 seconds to decide)

```bash
python main.py monitor run
```

If a company has a major event — new funding, layoffs, news spike — Scout fires an alert:

```
ALERT [HIGH] Acme Corp — Layoff signals detected + new funding
• 300 employees laid off in past 30 days
• $50M Series B closed last week
Score: 22

Recommended action: Reach out this week — budget just freed up from
layoffs, new capital means pressure to hire fast.
```

When you see an alert, run:

```bash
python main.py outreach "Acme Corp"
```

Pick an email variant and send. The angle is already chosen for you.

---

## Commands Reference

| Command | What it does |
|---------|-------------|
| `scout "Company"` | Research a company and generate a brief |
| `outreach "Company"` | Generate personalized email + LinkedIn messages |
| `score "Company"` | See detailed scoring breakdown for one company |
| `rank` | See all monitored companies ranked by priority |
| `monitor run` | Run daily checks on all monitored companies |
| `monitor add "Company"` | Add a company to monitoring list |
| `monitor list` | See all monitored companies |
| `alert list` | See recent alerts |

---

## Understanding the Score (100-point system)

Scout scores each company on 5 signals:

| Signal | Max Points | What it means |
|--------|-----------|----------------|
| **Funding** | 25 | Recent funding = budget available, pressure to grow |
| **Hiring** | 20 | Actively hiring = growing, likely open to new vendors |
| **News** | 15 | Lots of news = company is active and changing |
| **Reviews** | 15 | Very high or very low ratings = buying signals |
| **ICP Match** | 25 | How well this company fits your target profile |

**Grade thresholds:**
- **A** (80–100): Reach out this week
- **B** (60–79): Reach out within 2 weeks
- **C** (40–59): Nurture, check back next month
- **D** (0–39): Low priority, don't spend time

---

## Tips for Getting the Most Out of Scout

**1. Scout companies BEFORE you need them**
Don't wait until you're desperate for a sale. Add companies to your list proactively. By the time you're ready to reach out, Scout already has research and a snapshot to compare against.

**2. Use the alert angle, not the generic angle**
When Scout detects layoffs at a company, the email angle isn't "buy our product." It's "you just let go of 300 people — here's how to not lose the remaining 200 to burnout." That's the email that gets opened.

**3. Edit the emails slightly**
The generated emails are good starting points, not final drafts. Add one personal detail (mention their recent podcast, a mutual connection, a specific metric they shared) and reply rates will double.

**4. Check `rank` every Monday morning**
Before your week starts, spend 2 minutes on `rank`. You'll know exactly where to focus your energy for the next 5 days.

**5. Set it up as a daily cron job**
If you have a server or cloud setup, configure Scout to run `monitor run` automatically every morning at 8 AM. You'll arrive at work with a fresh prioritized list waiting.

---

## FAQ

**Q: Do I need any API keys?**
A: For basic operation, no. Scout has a built-in rule-based engine that works without any external API. For AI-powered email generation and richer research, add your OpenAI or Anthropic API key (free tiers available).

**Q: How is this different from just using LinkedIn or ChatGPT?**
A: LinkedIn tells you what a company does. Scout tells you when to reach out and why right now. ChatGPT can write an email, but it doesn't know that Acme Corp just raised $50M and is hiring 50 people this month. Scout combines real-time research + signal detection + email generation in one workflow.

**Q: What if I target a different industry?**
A: Scout works for any industry. Edit `config/icp.json` to match your target customers. The signal detection (funding, hiring, news) is industry-agnostic.

**Q: Can I use this for existing customers?**
A: Yes. Add existing customers to your monitoring list. If Scout detects they raised funding, hired a VP, or had negative news, that's a perfect expansion or check-in opportunity.

**Q: How is my data stored?**
A: All data is stored locally on your machine (or your own cloud server). Scout does not send your company list or research data to any third party.

---

## Pricing

Scout is self-hosted software — you run it on your own machine or server.

| Tier | Price | Companies | Outreach/Month |
|------|-------|-----------|---------------|
| Solo | $49/mo | 10 | 50 |
| Growth | $149/mo | 50 | Unlimited |
| Agency | $399/mo | Unlimited | Unlimited |

*All tiers include unlimited monitor runs and alerts. API access included in Growth and above.*

---

## Getting Help

- GitHub Issues: Report bugs or request features
- Documentation: `docs/` folder in this repository

---

*Scout — Know who to contact, when to reach out, and what to say. Every single day.*
