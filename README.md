# Job Crawler — LinkedIn & Indeed

A guide to run the LinkedIn and Indeed crawlers, configure filters, and use local JSON replay.

**Quick Start**
- **Setup:**
  - Create and activate a virtualenv, then install: `pip install -r requirements.txt`
  - Copy and fill `.env` with `APIFY_API_KEY`, `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_CHAT_ID`.

- **Run:**
  - LinkedIn: `python linkedin.py -c config.yaml --env .env`
  - Indeed: `python indeed.py -c config.yaml --env .env`

- **Run (local JSON replay):**
  - Provide a directory or single JSON file with `--local-json`:

```bash
python linkedin.py -c config.yaml --local-json data/config/20260606 --env .env
```

**Minimal Config (keys you’ll use often)**
- `search.positions`: list of job titles to search
- `search.distance`: radius (km) used for Indeed start URLs
- `search.indeed.job_type`: comma-separated values like `fulltime, permanent` (resolver converts to Indeed `sc` codes)
- `search.indeed.days_ago`: how many days back for Indeed (`fromage` / `startUrls`)
- `filters.hours_ago`: recency filter used by both scrapers
- `filters.nokeywords`: titles/descriptions to exclude (e.g., `Senior`, `Lead`)
- `filters.indeed.min_reviews_count`: minimum company reviews for Indeed
- `apify.indeed_actor_id` / `apify.actor_id`: actor IDs for Indeed and LinkedIn

Example snippet:

```yaml
search:
  positions: ["Cloud Engineer", "Software Engineer"]
  distance: 25
  indeed:
    job_type: "fulltime, permanent"
    days_ago: 3

filters:
  hours_ago: 48
  nokeywords: ["Senior", "Lead", "Manager"]
  indeed:
    min_reviews_count: 100

apify:
  indeed_actor_id: "<actor-id>"
  actor_id: "<linkedin-actor-id>"
```

**Storage layout**
- Saved Apify results are stored under:

  `data/<config_name>/<scraper>/<YYYYMMDD>/<position>/apify_response_<...>.json`

  Example: `data/config/indeed/20260606/cloud_engineer/apify_response_Cloud_Engineer_20260606_123456.json`

**Behavior notes**
- The first Telegram message after startup states which scraper is active: `LinkedIn connection test successful!` or `Indeed connection test successful!`.
- Indeed `search.indeed.job_type` accepts comma-separated inputs; the code deduplicates and concatenates the corresponding `sc` codes as needed.
- Job descriptions can be sent to the LLM for summarization based on `telegram.description_llm_threshold`.

**Common Commands**

```bash
# Show help
python linkedin.py --help
python indeed.py  --help

# Use a specific config
python linkedin.py -c config.yaml --env .env
python indeed.py  -c config.yaml  --env .env

# Local replay from a folder
python indeed.py -c config.yaml --local-json data/config/20260606 --env .env
```

**Quick Troubleshooting**
- No jobs: increase `search.indeed.days_ago`, raise `max_results`, or loosen `filters.nokeywords`.
- Telegram issues: verify `.env` credentials and that you started a chat with the bot.
- Apify issues: check `APIFY_API_KEY` and actor IDs.

If you want, I can also add a short example `config-quick.yaml` and an example cron line to schedule runs. 
