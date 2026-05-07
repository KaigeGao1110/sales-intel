# Research: Monitoring System Architecture

## Task
Design the system for continuous client monitoring after initial research.

## Focus Areas
1. **Check Frequency** - How often to check for updates (daily? weekly?)
2. **Change Detection** - How to detect meaningful vs trivial changes
3. **Alert Logic** - When to escalate to email/notification
4. **Storage** - How to store monitoring state (JSON files? SQLite?)
5. **Scalability** - How to handle 100+ monitored companies
6. **Cost** - Keeping Cloud Run costs low

## Output
Provide:
- Architecture diagram (text-based)
- Recommended check frequency for MVP
- Simple change detection algorithm
- Alert evaluation criteria
- Storage schema design
