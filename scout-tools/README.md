# Scout AI Sales Intelligence Toolkit

A unified command-line toolkit for accessing funding, news, and jobs intelligence to power sales prospecting and market research.

## Installation

```bash
pip install -r requirements.txt
chmod +x scout.py
```

## Quick Start

```bash
# View market overview
python scout.py report market

# Company intelligence report
python scout.py report company "TechFlow Solutions"

# Target list (min $10M raised, min 3 jobs)
python scout.py report targets 10000000 3
```

## Modules

### Funding Intelligence (`funding.py`)
Track funding rounds, investment amounts, and investor activity.

```bash
python funding.py "Company Name"          # Company funding data
python funding.py --recent 90             # Recent rounds
python funding.py --top 10                 # Top funded
python funding.py --report                 # Full report
```

### News Monitoring (`news.py`)
Track news articles and media coverage for buying signals.

```bash
python news.py "Company Name"              # Company news
python news.py --recent 30                 # Recent news
python news.py --signals                   # Buying signals
python news.py --report                    # Full report
```

### Jobs Analysis (`jobs.py`)
Analyze job postings to identify growth and hiring signals.

```bash
python jobs.py "Company Name"              # Company jobs
python jobs.py --trends                    # Hiring trends
python jobs.py --signals                   # Growth signals
python jobs.py --tech                      # Tech in demand
python jobs.py --report                    # Full report
```

### Reports (`report.py`)
Generate comprehensive intelligence reports.

```bash
python scout.py report company "Name"     # Company report
python scout.py report market              # Market overview
python scout.py report targets [raised] [jobs]  # Target list
python scout.py report export              # Export as JSON
```

## Data Files

- `companies.json` - Company funding and profile data
- `news_data.json` - News articles and media coverage
- `jobs_data.json` - Job postings and hiring data

## Requirements

- Python 3.10+
- No external dependencies (standard library only)

## License

MIT
