"""AWS Lambda entrypoint for LinkedIn/Indeed job crawlers.

Environment variables:
- SCRAPER: linkedin | indeed (default: linkedin)
- CONFIG_PATH: path to YAML config in deployment package (default: config.yaml)
- ENV_PATH: optional .env path (not required in Lambda)

Event overrides (optional):
- {"scraper": "indeed", "config_path": "config-hao.yaml"}
"""

import asyncio
import logging
import os
from typing import Any, Dict

from indeed import run_job_search as run_indeed_job_search
from linkedin import run_job_search as run_linkedin_job_search

# In Lambda the runtime pre-installs a root log handler, so basicConfig() in the
# scraper modules is a no-op and the root logger stays at WARNING. Set it to INFO
# here so logger.info(...) calls are emitted to CloudWatch.
logging.getLogger().setLevel(logging.INFO)


def _pick_scraper(event: Dict[str, Any]) -> str:
    event_scraper = str((event or {}).get("scraper", "")).strip().lower()
    env_scraper = str(os.getenv("SCRAPER", "linkedin")).strip().lower()
    scraper = event_scraper or env_scraper
    if scraper not in {"linkedin", "indeed"}:
        raise ValueError("SCRAPER must be 'linkedin' or 'indeed'")
    return scraper


def _pick_config(event: Dict[str, Any]) -> str:
    event_cfg = str((event or {}).get("config_path", "")).strip()
    env_cfg = str(os.getenv("CONFIG_PATH", "config.yaml")).strip()
    return event_cfg or env_cfg


def _pick_env_path(event: Dict[str, Any]) -> str:
    event_env = str((event or {}).get("env_path", "")).strip()
    env_env = str(os.getenv("ENV_PATH", ".env")).strip()
    return event_env or env_env


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    event = event or {}
    scraper = _pick_scraper(event)
    config_path = _pick_config(event)
    env_path = _pick_env_path(event)

    if scraper == "indeed":
        asyncio.run(run_indeed_job_search(config_path=config_path, local_json_path=None, env_path=env_path))
    else:
        asyncio.run(run_linkedin_job_search(config_path=config_path, local_json_path=None, env_path=env_path))

    return {
        "statusCode": 200,
        "message": "Job crawler run completed",
        "scraper": scraper,
        "config_path": config_path,
    }
