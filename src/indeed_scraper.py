"""
Indeed job scraper using Apify API
"""
from typing import List, Dict, Optional
from apify_client import ApifyClient
import logging
import json
import os
import glob
from datetime import datetime
from urllib.parse import urlencode, quote_plus

logger = logging.getLogger(__name__)


class IndeedScraper:
    def __init__(self, api_key: str, actor_id: str):
        """
        Initialize Indeed scraper with Apify credentials

        Args:
            api_key: Apify API key
            actor_id: Apify actor ID (misceres/indeed-scraper)
        """
        self.client = ApifyClient(api_key)
        self.actor_id = actor_id

    def search_jobs(
        self,
        positions: List[str],
        location: str = "Munich",
        distance: int = 25,
        days_ago: int = 7,
        max_results: int = 50,
        job_type: str = "fulltime",
        save_json: bool = True,
        output_base_dir: str = "data",
        config_name: Optional[str] = None,
        local_json_path: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for jobs on Indeed using Apify actor

        Args:
            positions: List of job titles to search for
            location: Location name
            distance: Search radius in kilometers
            days_ago: Only include jobs from this many days back
            max_results: Maximum number of results per search
            job_type: Job type filter (fulltime, parttime, contract, etc.)
            save_json: Whether to save raw Apify response to JSON file
            output_base_dir: Base directory for saving results
            config_name: Name of config for organizing output
            local_json_path: Optional path to local JSON file or directory to load results from

        Returns:
            List of job dictionaries (normalized to match LinkedIn format)
        """
        all_jobs = []

        scraper_folder = 'indeed'

        def build_start_url(position: str) -> str:
            country_code = 'de'
            region = 'Bayern' if location.lower() in ('munich', 'münchen') else ''
            location_text = f"{location}, {region}" if region else location
            job_type_code = self._resolve_job_type_code(job_type)
            params = {
                'q': position,
                'l': location_text,
                'fromage': days_ago,
                'radius': distance,
            }
            url = f"https://{country_code}.indeed.com/jobs?{urlencode(params, quote_via=quote_plus)}"
            if job_type_code:
                url += f"&sc=0kf%3Aattr%28{job_type_code}%29%3B"
            return url

        for position in positions:
            logger.info(f"Searching for {position} in {location} on Indeed")
            start_url = build_start_url(position)

            # If a local JSON path is provided, read files instead of calling Apify
            if local_json_path:
                files = []
                if os.path.isfile(local_json_path):
                    files = [local_json_path]
                else:
                    # Try to find files for this position under the provided directory
                    search_pattern = os.path.join(local_json_path, "**", scraper_folder, "**", f"*{position.replace(' ', '_')}*.json")
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
                                dataset_items.append(data)
                        logger.info(f"Loaded local JSON from {fname} ({len(dataset_items)} items so far)")
                    except Exception as e:
                        logger.error(f"Error loading local JSON {fname}: {e}")

                # Normalize Indeed jobs to match LinkedIn format
                for item in dataset_items:
                    normalized_job = self._normalize_indeed_job(item)
                    normalized_job['search_position'] = position
                    all_jobs.append(normalized_job)

                logger.info(f"Loaded {len(dataset_items)} jobs for {position} from local JSON")

                continue

            # Default behavior: call Apify actor
            run_input = {
                "followApplyRedirects": False,
                "maxItemsPerSearch": max_results,
                "parseCompanyDetails": False,
                "saveOnlyUniqueItems": True,
                "startUrls": [
                    {
                        "url": start_url
                    }
                ]
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

                # Normalize Indeed jobs to match LinkedIn format
                for item in dataset_items:
                    normalized_job = self._normalize_indeed_job(item)
                    normalized_job['search_position'] = position
                    all_jobs.append(normalized_job)

                logger.info(f"Found {len(dataset_items)} jobs for {position}")

            except Exception as e:
                logger.error(f"Error searching for {position}: {str(e)}")
                continue

        return all_jobs

    @staticmethod
    def _resolve_job_type_code(job_type: str) -> str:
        if not job_type:
            return "5QWDV|CF3CP%2COR"

        raw_values = [part.strip() for part in str(job_type).split(',') if part.strip()]
        if not raw_values:
            raw_values = [str(job_type).strip()]

        mapping = {
            'fulltime': '5QWDV|CF3CP%2COR',
            'full-time': '5QWDV|CF3CP%2COR',
            'vollzeit': '5QWDV|CF3CP%2COR',
            'festanstellung': '5QWDV',
            'permanent': '5QWDV',
        }

        codes = []
        seen = set()

        for value in raw_values:
            normalized = value.lower()
            code_value = mapping.get(normalized, value)
            for code in str(code_value).split('|'):
                code = code.strip()
                if code and code not in seen:
                    codes.append(code)
                    seen.add(code)

        if not codes:
            return "5QWDV|CF3CP%2COR"

        if len(codes) == 1:
            return codes[0]

        return '|'.join(codes)

    def _normalize_indeed_job(self, indeed_job: Dict) -> Dict:
        """
        Normalize Indeed job format to match LinkedIn format for compatibility with filters

        Args:
            indeed_job: Raw job data from Indeed scraper

        Returns:
            Normalized job dictionary
        """
        # Map Indeed fields to LinkedIn-compatible fields
        job_types = indeed_job.get('jobType') or indeed_job.get('employmentType') or []
        if isinstance(job_types, str):
            job_types = [job_types]

        posted_at = indeed_job.get('postingDateParsed') or indeed_job.get('postedAt') or indeed_job.get('scrapedAt')
        description = indeed_job.get('description', '')

        normalized = {
            'title': indeed_job.get('positionName', indeed_job.get('title', '')),
            'companyName': indeed_job.get('company', indeed_job.get('companyName', '')),
            'location': indeed_job.get('location', ''),
            'url': indeed_job.get('url', indeed_job.get('externalApplyLink', '')),
            'salary': indeed_job.get('salary'),
            'jobType': job_types,
            'employmentType': ', '.join(job_types) if job_types else '',
            'rating': indeed_job.get('rating'),
            'reviewsCount': indeed_job.get('reviewsCount'),
            'descriptionText': description,
            'description': description,
            'companyEmployeesCount': None,  # Not available in Indeed basic scraper
            'seniority': '',  # Not available in Indeed
            'isSponsored': bool(indeed_job.get('isSponsored', False)),
            'postedAt': posted_at,
            'rawPostedAt': indeed_job.get('postedAt'),
            # Keep original Indeed data for reference
            '_indeed_original': indeed_job
        }

        return normalized
