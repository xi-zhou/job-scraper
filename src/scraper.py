"""
LinkedIn job scraper using Apify API
"""
from typing import List, Dict, Optional
from urllib.parse import urlencode, quote_plus
from apify_client import ApifyClient
import logging
import json
import os
import glob
from datetime import datetime

logger = logging.getLogger(__name__)


class LinkedInScraper:
    def __init__(self, api_key: str, actor_id: str):
        """
        Initialize LinkedIn scraper with Apify credentials

        Args:
            api_key: Apify API key
            actor_id: Apify actor ID (curious_coder/linkedin-jobs-scraper)
        """
        self.client = ApifyClient(api_key)
        self.actor_id = actor_id

    def build_linkedin_url(
        self,
        keywords: str,
        location: str,
        geo_id: str,
        distance: int = 25,
        time_filter: str = "r86400",
        job_type: str = "F",
        experience_levels: str = "2,3,4"
    ) -> str:
        """
        Build LinkedIn job search URL with filters

        Args:
            keywords: Job title/keywords to search for
            location: Location name (e.g., "Munich")
            geo_id: LinkedIn geo ID for the location
            distance: Distance in km (default: 25)
            time_filter: Time filter (r86400 = last 24 hours, r604800 = last week)
            job_type: Job type (F = Full-time, P = Part-time, C = Contract, etc.)
            experience_levels: Comma-separated experience levels (2 = Internship, 3 = Entry level, 4 = Associate)

        Returns:
            Full LinkedIn search URL
        """
        base_url = "https://www.linkedin.com/jobs/search"

        params = {
            "keywords": keywords,
            "location": location,
            "geoId": geo_id,
            "distance": distance,
            "f_TPR": time_filter,
            "f_JT": job_type,
            "f_E": experience_levels,
            "position": 1,
            "pageNum": 0
        }

        url = f"{base_url}?{urlencode(params, quote_via=quote_plus)}"
        return url

    def search_jobs(
        self,
        positions: List[str],
        location: str = "Munich",
        geo_id: str = "100477049",
        distance: int = 25,
        max_results: int = 50,
        time_filter: str = "r86400",
        job_type: str = "F",
        experience_levels: str = "2,3,4",
        save_json: bool = True,
        output_base_dir: str = "data",
        config_name: Optional[str] = None,
        local_json_path: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for jobs on LinkedIn using Apify actor

        Args:
            positions: List of job titles to search for
            location: Location name
            geo_id: LinkedIn geo ID for location
            distance: Search radius in km
            max_results: Maximum number of results per search
            time_filter: Time filter (r86400 = 24h, r604800 = 1 week)
            job_type: Job type filter (F = Full-time)
            experience_levels: Experience level codes (2,3,4 = Entry level)
            save_json: Whether to save raw Apify response to JSON file

        Returns:
            List of job dictionaries
        """
        all_jobs = []

        scraper_folder = 'linkedin'

        for position in positions:
            logger.info(f"Searching for {position} in {location}")

            search_url = self.build_linkedin_url(
                keywords=position,
                location=location,
                geo_id=geo_id,
                distance=distance,
                time_filter=time_filter,
                job_type=job_type,
                experience_levels=experience_levels
            )

            logger.info(f"Search URL: {search_url}")

            # If a local JSON path is provided, read files instead of calling Apify
            if local_json_path:
                files = []
                if os.path.isfile(local_json_path):
                    files = [local_json_path]
                else:
                    # Try to find files for this position under the provided directory
                    search_pattern = os.path.join(local_json_path, '**', scraper_folder, '**', f'*{position.replace(' ', '_')}*.json')
                    files = glob.glob(search_pattern, recursive=True)

                    # If none found, fall back to any json files under path
                    if not files:
                        files = glob.glob(os.path.join(local_json_path, '**', '*.json'), recursive=True)

                dataset_items = []
                for fname in files:
                    try:
                        with open(fname, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                dataset_items.extend(data)
                            elif isinstance(data, dict) and 'items' in data:
                                dataset_items.extend(data.get('items', []))
                            else:
                                # assume file itself is a list-like dataset
                                dataset_items.append(data)
                        logger.info(f"Loaded local JSON from {fname} ({len(dataset_items)} items so far)")
                    except Exception as e:
                        logger.error(f"Error loading local JSON {fname}: {e}")

                # don't save again when using local files
                saved_count = 0
                for item in dataset_items:
                    item['search_position'] = position
                    all_jobs.append(item)

                logger.info(f"Loaded {len(dataset_items)} jobs for {position} from local JSON")

                continue

            # Default behavior: call Apify actor
            run_input = {
                "urls": [search_url],
                "count": max_results
            }

            try:
                run = self.client.actor(self.actor_id).call(run_input=run_input)

                dataset_items = self.client.dataset(run["defaultDatasetId"]).list_items().items

                if dataset_items and save_json:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                    # build multi-level output folder: base/config_name/scraper/date/jobname
                    date_str = datetime.now().strftime("%Y%m%d")
                    cfg = config_name or 'default_config'
                    job_folder = position.replace(' ', '_').lower()
                    out_dir = os.path.join(output_base_dir, cfg, scraper_folder, date_str, job_folder)
                    os.makedirs(out_dir, exist_ok=True)

                    filename = os.path.join(out_dir, f"apify_response_{position.replace(' ', '_')}_{timestamp}.json")

                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(dataset_items, f, indent=2, ensure_ascii=False)

                    saved_count = len(dataset_items)
                    logger.info(f"Saved raw Apify response to {filename} ({saved_count} items)")

                    if dataset_items:
                        logger.info(f"Available fields in first job: {list(dataset_items[0].keys())}")
                        if 'descriptionText' in dataset_items[0]:
                            desc_len = len(dataset_items[0].get('descriptionText', ''))
                            logger.info(f"Sample descriptionText length: {desc_len} characters")

                for item in dataset_items:
                    item['search_position'] = position
                    all_jobs.append(item)

                logger.info(f"Found {len(dataset_items)} jobs for {position}")

            except Exception as e:
                logger.error(f"Error searching for {position}: {str(e)}")
                continue

        return all_jobs
