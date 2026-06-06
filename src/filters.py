"""
Job filtering logic
"""
from typing import List, Dict
from datetime import datetime, timedelta
from dateutil import parser
import logging
import re

logger = logging.getLogger(__name__)


class JobFilter:
    def __init__(
        self,
        max_experience_years: int = 3,
        hours_ago: int = 24,
        exclude_sponsored: bool = True,
        min_employee_count: int = 1000,
        min_reviews_count: int = None,
        required_job_types: List[str] = None,
        keywords: List[str] = None,
        nokeywords: List[str] = None
    ):
        """
        Initialize job filter

        Args:
            max_experience_years: Maximum years of experience required
            hours_ago: Only include jobs posted within this many hours
            exclude_sponsored: Whether to exclude sponsored job posts
            min_employee_count: Minimum number of employees at company
            min_reviews_count: Minimum number of company reviews (Indeed only)
            required_job_types: Required job type values to match (Indeed only)
            keywords: Optional list of keywords to boost relevance
            nokeywords: Optional list of keywords to exclude jobs (if found in title or description)
        """
        self.max_experience_years = max_experience_years
        self.hours_ago = hours_ago
        self.exclude_sponsored = exclude_sponsored
        self.min_employee_count = min_employee_count
        self.min_reviews_count = min_reviews_count
        self.required_job_types = required_job_types or []
        self.keywords = keywords or []
        self.nokeywords = nokeywords or []

    def filter_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """
        Filter jobs based on criteria

        Args:
            jobs: List of job dictionaries from scraper

        Returns:
            Filtered list of jobs
        """
        filtered = []

        for job in jobs:
            include = self._should_include_job(job)
            if include:
                filtered.append(job)
            else:
                reasons = job.get('_filter_reasons', [])
                logger.info(f"Excluding job '{job.get('title', 'Unknown')}' for reasons: {reasons}")

        logger.info(f"Filtered {len(jobs)} jobs down to {len(filtered)} matching jobs")
        return filtered

    def _should_include_job(self, job: Dict) -> bool:
        """Check if job meets all filter criteria and record reasons when excluded"""
        reasons = []

        if self.exclude_sponsored and job.get('isSponsored', False):
            reasons.append('sponsored')

        ok, reason = self._is_recent_enough(job)
        if not ok:
            reasons.append(reason or 'too_old')

        ok, reason = self._meets_experience_requirements(job)
        if not ok:
            reasons.append(reason or 'experience')

        ok, reason = self._meets_employee_count_requirement(job)
        if not ok:
            reasons.append(reason or 'company_size')

        ok, reason = self._meets_reviews_count_requirement(job)
        if not ok:
            reasons.append(reason or 'reviews_count')

        ok, reason = self._meets_job_type_requirement(job)
        if not ok:
            reasons.append(reason or 'job_type')

        ok, matched = self._contains_nokeyword(job)
        if not ok:
            # record exact keywords that matched
            reasons.append({'nokeywords': matched})

        job['_filter_reasons'] = reasons

        return len(reasons) == 0

    def _is_recent_enough(self, job: Dict) -> (bool, str):
        """Check if job was posted within the time window. Returns (ok, reason)"""
        posted_at = job.get('postedAt') or job.get('listedAt') or job.get('postedDate')

        if not posted_at:
            logger.debug(f"No posted date for job: {job.get('title', 'Unknown')}")
            return True, None

        try:
            posted_date = parser.parse(posted_at)
            cutoff_date = datetime.now(posted_date.tzinfo) - timedelta(hours=self.hours_ago)

            is_recent = posted_date >= cutoff_date
            if not is_recent:
                reason = f"posted_at:{posted_at}"
                logger.debug(f"Job too old: {job.get('title', 'Unknown')} posted {posted_at}")
                return False, reason

            return True, None

        except Exception as e:
            logger.warning(f"Error parsing date {posted_at}: {e}")
            return True, None

    def _meets_experience_requirements(self, job: Dict) -> (bool, str):
        """Check if job meets experience level requirements. Returns (ok, reason)"""
        description = (job.get('descriptionText', job.get('description', '')) + ' ' + job.get('title', '')).lower()

        experience_patterns = [
            r'(\d+)\+?\s*years?\s+(?:of\s+)?experience',
            r'experience:\s*(\d+)\+?\s*years?',
            r'minimum\s+(\d+)\s+years?',
            r'at\s+least\s+(\d+)\s+years?'
        ]

        for pattern in experience_patterns:
            matches = re.findall(pattern, description)
            for match in matches:
                years = int(match)
                if years > self.max_experience_years:
                    reason = f"requires_years:{years}"
                    logger.debug(f"Job requires {years} years experience: {job.get('title', 'Unknown')}")
                    return False, reason

        seniority = job.get('seniority', '').lower()
        if any(term in seniority for term in ['senior', 'lead', 'principal', 'staff', 'expert']):
            reason = f"seniority:{seniority}"
            logger.debug(f"Excluding senior position: {job.get('title', 'Unknown')}")
            return False, reason

        return True, None

    def _meets_employee_count_requirement(self, job: Dict) -> (bool, str):
        """Check if company has minimum number of employees. Returns (ok, reason)"""
        employee_count = job.get('companyEmployeesCount')

        if employee_count is None:
            logger.debug(f"No employee count for job: {job.get('title', 'Unknown')} at {job.get('companyName', 'Unknown')}")
            return True, None

        try:
            count = int(employee_count)
            if count < self.min_employee_count:
                reason = f"company_size:{count}"
                logger.debug(f"Company too small ({count} employees): {job.get('companyName', 'Unknown')}")
                return False, reason
            return True, None
        except (ValueError, TypeError):
            logger.warning(f"Invalid employee count value: {employee_count}")
            return True, None

    def _meets_reviews_count_requirement(self, job: Dict) -> (bool, str):
        """Check if company has minimum number of reviews. Returns (ok, reason)"""
        if self.min_reviews_count is None:
            return True, None

        reviews_count = job.get('reviewsCount')
        if reviews_count is None:
            logger.debug(f"No reviews count for job: {job.get('title', 'Unknown')} at {job.get('companyName', 'Unknown')}")
            return False, 'reviews_count:missing'

        try:
            count = int(reviews_count)
            if count < self.min_reviews_count:
                reason = f"reviews_count:{count}"
                logger.debug(f"Company has too few reviews ({count}): {job.get('companyName', 'Unknown')}")
                return False, reason
            return True, None
        except (ValueError, TypeError):
            logger.warning(f"Invalid reviews count value: {reviews_count}")
            return False, 'reviews_count:invalid'

    def _meets_job_type_requirement(self, job: Dict) -> (bool, str):
        """Check if job type matches required job types. Returns (ok, reason)"""
        if not self.required_job_types:
            return True, None

        job_types = job.get('jobType') or job.get('employmentType') or []
        if isinstance(job_types, str):
            job_types = [job_types]

        normalized_job_types = ' '.join(str(job_type).lower() for job_type in job_types if job_type)
        if not normalized_job_types:
            logger.debug(f"No job type for job: {job.get('title', 'Unknown')}")
            return False, 'job_type:missing'

        if any(required.lower() in normalized_job_types for required in self.required_job_types):
            return True, None

        return False, f"job_type:{','.join(str(job_type) for job_type in job_types)}"

    def _contains_nokeyword(self, job: Dict) -> (bool, list):
        """Check if job contains any excluded keywords in title or description.
        Returns (ok, matched_keywords) where ok=False if any matched, and matched_keywords is list of matches.
        """
        if not self.nokeywords:
            return True, []

        title = job.get('title', '').lower()
        description = job.get('descriptionText', job.get('description', '')).lower()
        combined_text = f"{title} {description}"

        matched = []
        for nokeyword in self.nokeywords:
            if nokeyword.lower() in combined_text:
                matched.append(nokeyword)

        if matched:
            logger.debug(f"Excluding job containing nokeywords {matched}: {job.get('title', 'Unknown')}")
            return False, matched

        return True, []

    def calculate_relevance_score(self, job: Dict) -> float:
        """
        Calculate relevance score based on keyword matching

        Returns:
            Score between 0 and 1
        """
        if not self.keywords:
            return 0.5

        description = (
            job.get('descriptionText', job.get('description', '')) + ' ' +
            job.get('title', '') + ' ' +
            ' '.join(job.get('skills', []))
        ).lower()

        matches = sum(1 for keyword in self.keywords if keyword.lower() in description)
        score = matches / len(self.keywords)

        return score
