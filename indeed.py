"""
Indeed Job Crawler - Main Script
Searches for jobs matching your criteria and sends notifications via Telegram
"""
import asyncio
import argparse
import logging
import os
import sys
from typing import List, Dict, Optional
import yaml
from dotenv import load_dotenv

from src.indeed_scraper import IndeedScraper
from src.filters import JobFilter
from src.telegram_bot import TelegramNotifier
from src.llm_processor import JobDescriptionProcessor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> Dict:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        sys.exit(1)


def load_environment(env_path: str = '.env'):
    """Load environment variables from a .env file (path configurable)"""
    load_dotenv(dotenv_path=env_path)

    required_vars = ['APIFY_API_KEY', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error(f"Please copy .env.example to {env_path} and fill in your credentials or pass a different env file with --env")
        sys.exit(1)

    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    if not anthropic_key:
        logger.warning("ANTHROPIC_API_KEY not found - LLM processing will be disabled")

    return {
        'apify_api_key': os.getenv('APIFY_API_KEY'),
        'telegram_bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
        'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID'),
        'anthropic_api_key': anthropic_key
    }


async def run_job_search(config_path: str = "config.yaml", local_json_path: Optional[str] = None, env_path: str = '.env'):
    """Main function to run the job search"""
    logger.info("🚀 Starting Indeed Job Crawler")

    config = load_config(config_path)
    env = load_environment(env_path)

    search_config = config.get('search', {})
    indeed_search = search_config.get('indeed', {})
    filters_config = config.get('filters', {})
    indeed_filters = filters_config.get('indeed', {})

    # Use Indeed-specific actor ID from config, with a safe default
    indeed_actor_id = config.get('apify', {}).get('indeed_actor_id', config.get('apify', {}).get('actor_id', "misceres/indeed-scraper"))

    def normalize_required_job_types(job_type_value):
        if not job_type_value:
            return ['fulltime', 'vollzeit']

        if isinstance(job_type_value, list):
            values = job_type_value
        else:
            values = [job_type_value]

        normalized = []
        for value in values:
            lowered = str(value).lower()
            normalized.append(lowered)
            if lowered in ('fulltime', 'vollzeit', 'f'):
                normalized.extend(['fulltime', 'vollzeit'])

        return list(dict.fromkeys(normalized))

    scraper = IndeedScraper(
        api_key=env['apify_api_key'],
        actor_id=indeed_actor_id
    )

    job_filter = JobFilter(
        max_experience_years=3,
        hours_ago=indeed_filters.get('hours_ago', filters_config.get('hours_ago', 48)),
        exclude_sponsored=search_config.get('exclude_sponsored', True),
        min_employee_count=filters_config.get('min_employee_count', 0),
        min_reviews_count=indeed_filters.get('min_reviews_count', filters_config.get('min_reviews_count')),
        required_job_types=normalize_required_job_types(indeed_search.get('job_type', search_config.get('job_type', 'fulltime'))),
        keywords=indeed_search.get('keywords', search_config.get('keywords', [])),
        nokeywords=indeed_filters.get('nokeywords', filters_config.get('nokeywords', []))
    )

    llm_processor = None
    if env['anthropic_api_key'] and config['llm']['enabled']:
        logger.info("Initializing LLM processor for job descriptions")
        llm_processor = JobDescriptionProcessor(
            api_key=env['anthropic_api_key'],
            model=config['llm']['model']
        )
    else:
        logger.info("LLM processing disabled - descriptions will be truncated")

    notifier = TelegramNotifier(
        bot_token=env['telegram_bot_token'],
        chat_id=env['telegram_chat_id'],
        llm_processor=llm_processor,
        scraper_name="Indeed"
    )

    logger.info("📡 Testing Telegram connection...")
    if not await notifier.test_connection():
        logger.error("Failed to connect to Telegram. Please check your credentials.")
        sys.exit(1)

    logger.info("🔍 Searching for jobs on Indeed...")
    # derive a simple config name from the config file path (without extension)
    config_name = os.path.splitext(os.path.basename(config_path))[0]

    jobs = scraper.search_jobs(
        positions=indeed_search.get('positions', search_config.get('positions', [])),
        location=indeed_search.get('location', search_config.get('location', 'Munich')),
        distance=indeed_search.get('distance', search_config.get('distance', 25)),
        days_ago=indeed_search.get('days_ago', 7),
        max_results=indeed_search.get('max_results', search_config.get('max_results', 50)),
        job_type=indeed_search.get('job_type', search_config.get('job_type', 'fulltime')),
        save_json=os.getenv("AWS_LAMBDA_FUNCTION_NAME") is None,
        output_base_dir=config.get('output_dir', 'data'),
        config_name=config_name,
        local_json_path=local_json_path
    )

    logger.info(f"Found {len(jobs)} total jobs from Indeed")

    logger.info("🔎 Filtering jobs...")
    filtered_jobs = job_filter.filter_jobs(jobs)

    for job in filtered_jobs:
        job['relevance_score'] = job_filter.calculate_relevance_score(job)

    filtered_jobs.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

    logger.info(f"✅ {len(filtered_jobs)} jobs match your criteria")

    logger.info("📤 Sending notifications to Telegram...")
    await notifier.send_job_notifications(
        jobs=filtered_jobs,
        max_jobs_per_message=config['telegram']['max_jobs_per_message'],
        description_length=config['telegram']['description_llm_threshold']
    )

    logger.info("🎉 Job search completed successfully!")


def main():
    """Entry point"""
    parser = argparse.ArgumentParser(
        description='Indeed Job Crawler - Search for jobs and send notifications via Telegram'
    )
    parser.add_argument(
        '-c', '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '-e', '--env',
        type=str,
        default='.env',
        help='Path to environment file (default: .env)'
    )
    parser.add_argument(
        '--local-json',
        type=str,
        default=None,
        help='Path to a local JSON file or directory to load results from instead of calling Apify'
    )

    args = parser.parse_args()

    try:
        asyncio.run(run_job_search(args.config, local_json_path=args.local_json, env_path=args.env))
    except KeyboardInterrupt:
        logger.info("\n👋 Job search interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error during job search: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
