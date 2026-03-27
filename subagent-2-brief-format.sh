#!/bin/bash
echo "=== SUBAGENT 2: Brief Format Research ===" > results-brief-format.txt
echo "Timestamp: $(date)" >> results-brief-format.txt
echo "" >> results-brief-format.txt

# Brief Structure
echo "## RECOMMENDED BRIEF STRUCTURE" >> results-brief-format.txt
echo "" >> results-brief-format.txt
cat >> results-brief-format.txt << 'STRUCTURE'
# Company Brief: [COMPANY NAME]

## 1. Company Overview (3 sentences)
- Industry, size, location, what they do

## 2. Current Challenges (THE KEY SECTION)
What problems is this company most likely facing RIGHT NOW?
- Look for: recent layoffs, negative press, product issues, competitor threats
- Hiring freezes? → budget problems, cost-cutting mode
- Rapid hiring? → scaling pain, need automation
- New funding? → ready to spend, solving pain points
- Leadership changes? → strategic pivot likely

## 3. Recent Signals (Last 3-6 months)
- News events that indicate challenges
- Job posting trends
- Product launches or issues
- Customer complaints (G2, Trustpilot)

## 4. Likely Solutions Needed
Based on challenges above:
- What category of solution would help?
- What specific features matter?
- What budget/authority exists?

## 5. Conversation Starters
2-3 specific talking points based on research
- Recent news they would have seen
- Industry trend affecting them
- A question that shows you did homework

## 6. Risk Factors
- Why they might NOT buy
- Current vendor relationships
- Internal obstacles

---
Generated: [DATE] | Data sources: [LIST]
STRUCTURE

echo "" >> results-brief-format.txt

# Problem Indicators
echo "## 7 KEY PROBLEM INDICATORS" >> results-brief-format.txt
echo "" >> results-brief-format.txt
cat >> results-brief-format.txt << 'INDICATORS'
1. LAYOFFS/COST CUTTING → Need efficiency tools, proof of ROI
2. RAPID GROWTH HIRING → Scaling problems, onboarding automation
3. NEW FUNDING ROUND → Budget available, pressure to grow fast
4. LEADERSHIP CHANGES → Strategy shifts, new priorities, vendor churn
5. NEGATIVE PRESS/REVIEWS → Customer experience focus needed
6. COMPETITOR ACTIVITY → Market pressure, differentiation urgency
7. PRODUCT ISSUES/DELAYS → Engineering capacity, technical debt
INDICATORS

echo "" >> results-brief-format.txt

# Example Prompt
echo "## BRIEF GENERATION PROMPT" >> results-brief-format.txt
echo "" >> results-brief-format.txt
cat >> results-brief-format.txt << 'PROMPT'
You are a sales intelligence analyst. Given the following research data 
about [COMPANY NAME], generate a 1-page sales brief.

RESEARCH DATA:
[Insert aggregated news, reviews, job postings, funding data here]

TASK:
1. Identify the TOP 2-3 problems this company most likely needs solved RIGHT NOW
2. Rate confidence level (High/Medium/Low) based on available data
3. Suggest what type of solution would address each problem
4. Generate 2 conversation starters that show you understand their business

FORMAT: Use markdown, keep it to 1 page, focus on actionable insights.
PROMPT

echo "" >> results-brief-format.txt

# Sample Brief
echo "## SAMPLE BRIEF (FICTIONAL: 'TechFlow Inc')" >> results-brief-format.txt
echo "" >> results-brief-format.txt
cat >> results-brief-format.txt << 'SAMPLE'
# Company Brief: TechFlow Inc

## 1. Company Overview
TechFlow is a 200-person B2B SaaS company in the project management space, 
based in Austin TX. They serve mid-market companies (100-1000 employees) 
with their flagship product FlowSync.

## 2. Current Challenges

**HIGH CONFIDENCE: Scaling Pain (Score: 8/10)**
- Hired 50 people in Q4 2023, another 40 in Q1 2024
- Engineering team grew 40% → code review bottlenecks, deployment frequency dropped
- Glassdoor reviews mention "hard to scale" and "process breakdowns"

**MEDIUM CONFIDENCE: Customer Churn Risk (Score: 6/10)**
- G2 reviews show 3 negative reviews since Jan citing "outages" and "support slow"
- Trustpilot rating dropped from 4.2 to 3.8
- Recent layoffs in customer success team (15% of CS staff)

## 3. Recent Signals
- Jan 2024: Series B closed ($40M)
- Feb 2024: New VP Engineering hired from Salesforce
- Mar 2024: 12 job postings for "platform" and "infrastructure" roles
- G2 reviews mention API reliability issues

## 4. Likely Solutions Needed
1. **Developer Productivity Tools** - Code review automation, deployment tooling
2. **Customer Success Automation** - Self-service onboarding, reduce CS headcount ratio
3. **Reliability/Observability** - Fix outages before they lose more customers

## 5. Conversation Starters
- "I noticed you just hired a new VP Eng - congronts on the Series B! 
  What's the team's top priority for 2024?"
- "I saw some G2 reviews mentioning reliability issues - have you looked 
  into observability solutions?"

## 6. Risk Factors
- New VP Eng may want to build vs buy
- Series B means they have runway - not desperate
- Existing vendor relationships (Jira, Slack) to overcome

---
Generated: 2024-03-15 | Sources: NewsAPI, G2, Crunchbase, LinkedIn Jobs
SAMPLE

echo "" >> results-brief-format.txt
echo "=== SUBAGENT 2 COMPLETE ===" >> results-brief-format.txt
