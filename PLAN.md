# Scout - Sales Intelligence Agent System
## Phase 1 MVP Plan

**Project:** Scout  
**Type:** Multi-Agent Sales Intelligence System  
**Date:** 2026-03-27  
**Status:** Phase 1 Planning  

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SCOUT SYSTEM                                 │
│                    (Cloud Run - Serverless)                         │
└─────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │  LEVEL 0        │
                              │  SCOUT          │
                              │  (Main Session) │
                              │  - Orchestrates │
                              │  - Generates    │
                              │    Briefs       │
                              │  - Manages      │
                              │    Monitoring   │
                              └────────┬────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
              ▼                        ▼                        │
     ┌─────────────────┐     ┌─────────────────┐                │
     │  LEVEL 1        │     │  LEVEL 1        │                │
     │  RESEARCH AGENT │     │  MONITOR AGENT  │                │
     │                 │     │                 │                │
     │ Spawns research │     │ Spawns watchers │                │
     │ sub-agents      │     │ for monitoring  │                │
     └────────┬────────┘     └────────┬────────┘                │
              │                        │                          │
              ▼                        ▼                          │
     ┌─────────────────────────────────────────────────────────────────┐
     │                    LEVEL 2: RESEARCHERS (run, single-use)      │
     ├─────────────────┬─────────────────┬───────────────────────────┤
     │ LinkedIn        │ News            │ Review                    │
     │ Researcher      │ Researcher      │ Researcher                │
     │                 │                 │                           │
     │ - Employee      │ - News search   │ - G2 reviews              │
     │   counts        │ - Brave Search  │ - Trustpilot              │
     │ - Hiring trends │ - NewsAPI       │ - Sentiment analysis      │
     └─────────────────┴─────────────────┴───────────────────────────┘
                                       │
                                       ▼
     ┌─────────────────────────────────────────────────────────────────┐
     │                 LEVEL 2: WATCHERS (run, cron-triggered)        │
     ├─────────────────┬─────────────────┬───────────────────────────┤
     │ News            │ Job             │ Funding                   │
     │ Watcher         │ Watcher         │ Watcher                   │
     │                 │                 │                           │
     │ Daily checks    │ Daily checks    │ Weekly checks             │
     │ Sentiment delta │ New postings    │ New rounds                │
     └─────────────────┴─────────────────┴───────────────────────────┘
                                       │
                                       ▼
     ┌─────────────────────────────────────────────────────────────────┐
     │                     DATA STORE (JSON/SQLite)                     │
     │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
     │  │  companies  │  │  snapshots  │  │    alerts   │             │
     │  │   .json     │  │     /       │  │   _log.json │             │
     │  └─────────────┘  └─────────────┘  └─────────────┘             │
     └─────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │   NOTIFICATIONS │
                              │  Email / Slack  │
                              └─────────────────┘
```

---

## 2. Agent Design

### 2.1 Level 0: Scout (Main Session)
**Responsibilities:**
- Accept user commands: `//scout [company-name]`
- Spawn Level 1 agents (Research Agent, Monitor Agent)
- Generate 1-page brief from research results
- Manage monitored companies list

**Interface:**
- CLI command: `//scout Acme Corp`
- Returns: Markdown brief + confirmation of monitoring setup

### 2.2 Level 1: Research Agent
**Responsibilities:**
- Spawn and manage Level 2 researcher agents
- Aggregate data from multiple research sources
- Coordinate parallel research tasks

**Spawns:**
- LinkedIn Researcher (Level 2)
- News Researcher (Level 2)
- Review Researcher (Level 2)

### 2.3 Level 2: LinkedIn Researcher (run, single-use)
**Responsibilities:**
- Fetch employee counts and hiring trends
- Identify leadership changes
- Track company growth signals

**Data Source:** LinkedIn (via web scraping or API)

### 2.4 Level 2: News Researcher (run, single-use)
**Responsibilities:**
- Search for company news (Brave Search API)
- Fetch mainstream news (NewsAPI)
- Analyze sentiment from recent coverage

**Data Sources:**
| Source | API | Free Tier | Purpose |
|--------|-----|-----------|---------|
| Brave Search | brave-search | 2000/mo | Web + News search |
| NewsAPI | newsapi.org | 100/day | Mainstream news |

### 2.5 Level 2: Review Researcher (run, single-use)
**Responsibilities:**
- Fetch G2 and Trustpilot reviews
- Analyze rating trends and sentiment
- Identify customer complaints and praise patterns

**Data Sources:** G2, Trustpilot (via web scraping)

### 2.6 Level 1: Monitor Agent
**Responsibilities:**
- Spawn and manage Level 2 watcher agents
- Coordinate monitoring schedule
- Aggregate change signals

**Spawns:**
- News Watcher (Level 2, cron-triggered)
- Job Watcher (Level 2, cron-triggered)
- Funding Watcher (Level 2, weekly)

### 2.7 Level 2: News Watcher (run, cron-triggered)
**Responsibilities:**
- Run daily (triggered by Cloud Run Cron)
- Check monitored companies for news
- Store snapshots of current news state
- Detect news volume spikes and sentiment shifts

**Check Frequency:** Daily

### 2.8 Level 2: Job Watcher (run, cron-triggered)
**Responsibilities:**
- Monitor job posting changes
- Detect hiring surges or slowdowns
- Track new role categories

**Check Frequency:** Daily

### 2.9 Level 2: Funding Watcher (run, weekly)
**Responsibilities:**
- Check for new funding rounds
- Track valuation changes
- Detect layoffs or restructuring

**Check Frequency:** Weekly

### 2.10 Alert Agent
**Responsibilities:**
- Evaluate change significance (scoring system)
- Deduplicate similar alerts
- Route to correct notification channel
- Log all alerts to alerts_log.json

**Significance Scoring:**
| Signal | Points |
|--------|--------|
| Layoffs announced | +10 |
| New funding round | +8 |
| Rating drop > 0.3 stars | +7 |
| Sentiment shift (pos→neg) | +6 |
| News volume spike (>3 in 24h) | +4 |
| Minor news | +1 |

**Alert Threshold:** Score ≥ 10 → Send alert

---

## 3. Data Model

### 3.1 companies.json
```json
{
  "companies": [
    {
      "id": "uuid-v4",
      "name": "Acme Corp",
      "domain": "acme.com",
      "added_date": "2024-01-15",
      "last_checked": "2024-03-20T10:30:00Z",
      "status": "active|paused",
      "alert_channels": ["email", "slack"],
      "alert_email": "sales@company.com"
    }
  ]
}
```

### 3.2 snapshots/{company_id}_{date}.json
```json
{
  "company_id": "uuid",
  "company_name": "Acme Corp",
  "check_date": "2024-03-20",
  "news": [
    {
      "title": "...",
      "url": "...",
      "published": "2024-03-19",
      "sentiment": "positive|neutral|negative"
    }
  ],
  "jobs": {
    "total_postings": 45,
    "new_last_7_days": 12,
    "keywords": ["engineer", "sales", "security"]
  },
  "reviews": {
    "g2_rating": 4.2,
    "trustpilot_rating": 3.8,
    "recent_negative": 3
  },
  "funding": {
    "last_round": "Series B",
    "amount": "$40M",
    "date": "2024-01-15",
    "valuation": "$200M"
  }
}
```

### 3.3 alerts_log.json
```json
{
  "alerts": [
    {
      "id": "uuid",
      "company_id": "uuid",
      "company_name": "Acme Corp",
      "alert_date": "2024-03-20T14:00:00Z",
      "type": "news|layoff|funding|review|jobs",
      "severity": "high|medium|low",
      "title": "Acme Corp announces layoffs",
      "summary": "...",
      "score": 10,
      "notified": true,
      "notification_date": "2024-03-20T14:05:00Z",
      "channels": ["email"]
    }
  ]
}
```

---

## 4. Tech Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| Language | Python 3.11+ | Core logic |
| Deployment | Google Cloud Run | Serverless, cheap at idle |
| Scheduling | Cloud Run Jobs + Cron | Daily monitoring trigger |
| Data Storage | JSON files + SQLite | Simple, no DB for MVP |
| Search API | Brave Search API | 2000 requests/month free |
| News API | NewsAPI.org | 100 requests/day free |
| Company Data | Clearbit | 5000 requests/month free |
| Funding Data | Crunchbase | Free tier (limited) |
| Email | Gmail API | Via Google Workspace |
| Notifications | Slack Webhook | Optional alternative |

### Project Structure
```
scout/
├── main.py              # CLI entry point
├── agents/
│   ├── __init__.py
│   ├── scout.py         # Main agent
│   ├── research.py      # Research subagent
│   ├── monitor.py       # Monitor subagent
│   └── alert.py         # Alert subagent
├── services/
│   ├── __init__.py
│   ├── brave_search.py  # Brave API wrapper
│   ├── news_api.py      # NewsAPI wrapper
│   ├── clearbit.py      # Clearbit wrapper
│   └── crunchbase.py    # Crunchbase wrapper
├── storage/
│   ├── __init__.py
│   ├── companies.py     # companies.json CRUD
│   ├── snapshots.py     # Snapshot storage
│   └── alerts.py        # Alert logging
├── prompts/
│   └── brief_template.py # Brief generation prompts
├── data/
│   ├── companies.json
│   ├── alerts_log.json
│   └── snapshots/
├── requirements.txt
├── Dockerfile
└── cloudrun-job.yaml
```

---

## 5. Phase 1 MVP Task List

### Week 1: Core Infrastructure
- [ ] **T1.1** Set up project structure and virtual environment
- [ ] **T1.2** Create Dockerfile for Cloud Run
- [ ] **T1.3** Implement storage layer (companies.json, snapshots/)
- [ ] **T1.4** Implement Brave Search API wrapper
- [ ] **T1.5** Implement NewsAPI wrapper

### Week 2: Research Agent
- [ ] **T2.1** Implement Research Subagent
- [ ] **T2.2** Create brief generation prompt template
- [ ] **T2.3** Implement Clearbit company enrichment
- [ ] **T2.4** Implement Crunchbase funding data fetch
- [ ] **T2.5** End-to-end test: `//scout Acme Corp` → brief

### Week 3: Monitoring Agent
- [ ] **T3.1** Implement Monitor Subagent
- [ ] **T3.2** Implement change detection engine
- [ ] **T3.3** Implement significance scoring
- [ ] **T3.4** Create Cloud Run Job configuration
- [ ] **T3.5** Set up daily cron trigger

### Week 4: Alert Agent & Notifications
- [ ] **T4.1** Implement Alert Subagent
- [ ] **T4.2** Implement deduplication logic
- [ ] **T4.3** Implement Gmail API integration
- [ ] **T4.4** Implement Slack webhook option
- [ ] **T4.5** Alert logging to alerts_log.json

### Week 5: Integration & Testing
- [ ] **T5.1** Full system integration test
- [ ] **T5.2** Test with 5 real companies
- [ ] **T5.3** Verify email notifications work
- [ ] **T5.4** Cost estimation validation
- [ ] **T5.5** Write user documentation

### Parallelization Opportunities
| Tasks | Can Run In Parallel |
|-------|---------------------|
| T1.4, T1.5 | Yes |
| T2.2, T2.3, T2.4 | Yes |
| T4.3, T4.4 | Yes |
| T5.2 (with different companies) | Yes |

---

## 6. Brief Output Format

```markdown
# Company Brief: [COMPANY NAME]

## 1. Company Overview
[3 sentences: industry, size, location, what they do]

## 2. Current Challenges
**HIGH CONFIDENCE: [Challenge Name] (Score: X/10)**
- Evidence point 1
- Evidence point 2

**MEDIUM CONFIDENCE: [Challenge Name] (Score: X/10)**
- Evidence point 1

## 3. Recent Signals (Last 3-6 months)
- [Signal 1] - [what it means]
- [Signal 2] - [what it means]

## 4. Likely Solutions Needed
1. **[Solution Category]** - [specific features]
2. **[Solution Category]** - [specific features]

## 5. Conversation Starters
- "..."
- "..."

## 6. Risk Factors
- [Why they might not buy]
- [Current vendorlock-in]

---
Generated: [DATE] | Confidence: Based on [X] data sources
```

---

## 7. Problem Indicators (for Brief Generation)

| Indicator | Signal | Likely Problem | Solution Category |
|-----------|--------|----------------|------------------|
| Layoffs announced | Cost cutting | Efficiency, ROI | Proof of value |
| Rapid hiring | Scaling | Onboarding, process | Automation |
| New funding | Budget available | Grow fast | Tools for speed |
| Leadership change | Strategy shift | New priorities | New vendors |
| Negative reviews | Customer issues | Experience | CX tools |
| Competitor activity | Market pressure | Differentiation | Competitive edge |
| Product delays | Capacity | Technical debt | Dev productivity |

---

## 8. How to Test the MVP

### Test 1: Manual Brief Generation
```bash
# Research and generate brief for a known company
python main.py scout "TechFlow Inc"

# Expected: Markdown brief returned in < 30 seconds
```

### Test 2: Monitored Company Check
```bash
# Add company to monitoring
python main.py monitor add "TechFlow Inc" --email=your@email.com

# Manually trigger check
python main.py monitor check "TechFlow Inc"

# Expected: Snapshot created, no alert (no changes yet)
```

### Test 3: Change Detection
```bash
# Simulate news by manually adding to snapshot
# Then run check again
python main.py monitor check "TechFlow Inc"

# Expected: Change detected, scored, alert if threshold met
```

### Test 4: Email Notification
```bash
# Trigger alert manually
python main.py alert test --email=your@email.com

# Expected: Email received via Gmail API
```

### Test 5: Cost Validation
```bash
# Run full monitoring cycle locally
time python -c "from agents.monitor import MonitorAgent; MonitorAgent().run_all()"

# Expected: < 30 seconds for 10 companies
# Cloud Run cost: ~$0.01 per full cycle
```

### Test Companies (for MVP testing)
1. **Notion** - Recent pricing changes, rapid growth
2. **Figma** - Recent layoffs in tech, Adobe deal failed
3. **Stripe** - Recent valuation cut, hiring slowdown
4. **OpenAI** - Rapid growth, Microsoft partnership
5. **WeWork** - Past bankruptcy, recent recovery

---

## 9. API Keys Needed (MVP)

| Service | Sign Up | Free Tier | Cost after |
|---------|---------|-----------|------------|
| Brave Search | brave.com/search/api | 2000/mo | $3/1000 |
| NewsAPI | newsapi.org | 100/day | $10/mo |
| Clearbit | clearbit.com | 5000/mo | $50/mo |
| Crunchbase | crunchbase.com | Limited | $29/mo |
| Gmail API | console.cloud.google.com | Standard GCP | Included |

**Total MVP Cost:** $0/month (within free tiers)  
**MVP→Production:** ~$50-100/month for increased API limits

---

## 10. Spawn Architecture Rules

The Scout system uses a multi-level spawn architecture to delegate tasks to specialized agents.

### Hierarchy

```
Level 0: Scout (main session - Kaige's interface)
  └── Level 1: Research Agent (spawns researchers)
        └── Level 2: LinkedIn Researcher (run, single-use)
        └── Level 2: News Researcher (run, single-use)
        └── Level 2: Review Researcher (run, single-use)
  └── Level 1: Monitor Agent (spawns watchers)
        └── Level 2: News Watcher (run, cron-triggered)
        └── Level 2: Job Watcher (run, cron-triggered)
        └── Level 2: Funding Watcher (run, weekly)
```

### Rules

| Rule | Description |
|------|-------------|
| **Max spawn depth** | 4 levels from main session |
| **Max direct children** | 2 per agent (Level 1 agents have 3 children in MVP for initial build) |
| **Level 3+ agents** | run mode only, no persistent sessions |
| **Level 4** | Forbidden without main session approval |

### Mode Guidelines

| Mode | Use Case | Persistence |
|------|----------|-------------|
| **run** | One-shot tasks, research missions | No - single execution |
| **session** | Ongoing coordination, complex orchestration | Yes - maintains context |

### Why This Architecture

- **Token efficiency**: Each level accumulates context in its own session, not main
- **Specialization**: Each sub-agent optimized for one task (LinkedIn, News, Jobs, Funding)
- **Debugging**: Clear parent-child relationship for tracing
- **Cost control**: Level 3+ agents are short-lived runs
- **Parallelization**: Research Agent spawns researchers in parallel for speed

### Implementation Notes

- Scout (Level 0) never does research directly - always delegates
- Research Agent and Monitor Agent (Level 1) coordinate but don't execute
- Level 2 agents are single-use: spawned per-task, run, then terminate
- Watchers use cron triggers (Cloud Run Jobs) rather than persistent polling

---

## 11. Next Steps After Phase 1

1. **LinkedIn Integration** - Employee counts, hiring trends
2. **G2/Trustpilot API** - Direct review access
3. **CRM Integration** - Salesforce/HubSpot sync
4. **Multi-user** - Team collaboration
5. **Analytics Dashboard** - Monitor performance metrics

---

*Plan compiled: 2026-03-27*  
*Research by: Scout Project Coordinator*  
*Phase 1 Target: Functional MVP in 5 weeks*
