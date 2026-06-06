"""
LLM processor for job descriptions
Uses Claude API to summarize and extract key information from long job descriptions
"""
import logging
from typing import Dict, Optional
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class JobDescriptionProcessor:
    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-20241022"):
        """
        Initialize LLM processor with Claude API

        Args:
            api_key: Anthropic API key
            model: Claude model to use (haiku is fastest and cheapest)
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def process_description(self, job: Dict, max_tokens: int = 300) -> str:
        """
        Process a job description using Claude API

        Args:
            job: Job dictionary containing title, company, and descriptionText
            max_tokens: Maximum tokens for response

        Returns:
            Processed description with key skills and tasks
        """
        title = job.get('title', 'Unknown Position')
        company = job.get('companyName', 'Unknown Company')
        description = job.get('descriptionText', job.get('description', ''))

        if not description:
            return "No description available"

        prompt = f"""Analyze this job posting and extract the most important information in a concise format.

Job Title: {title}
Company: {company}

Job Description:
{description}

Please provide a clean summary with:
1. Required Skills: List the key technical skills and technologies (comma-separated)
2. Main Responsibilities: Summarize the primary job tasks in 2-3 bullet points

Format your response as plain text using:
- Use "Required Skills:" as a header
- Use "Main Responsibilities:" as a header
- Use simple bullet points with "•" character
- NO markdown formatting (no asterisks, no hashtags, no dashes for bullets)
- Keep it brief and focused on what matters most for a job seeker"""

        try:
            logger.info(f"Processing job description with LLM for: {title} at {company}")

            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            processed_text = message.content[0].text
            logger.info(f"Successfully processed description for: {title}")

            return processed_text

        except Exception as e:
            logger.error(f"Error processing description with LLM: {str(e)}")
            return description[:500] + "..." if len(description) > 500 else description

    def should_process_with_llm(self, description: str, threshold: int = 0) -> bool:
        """
        Determine if description should be processed with LLM

        Args:
            description: Job description text
            threshold: Character threshold for LLM processing (set to 0 to process all)

        Returns:
            True to always process with LLM
        """
        return len(description) > threshold
