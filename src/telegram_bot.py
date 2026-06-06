"""
Telegram bot for sending job notifications
"""
from typing import List, Dict, Optional
import logging
from datetime import datetime
from dateutil import parser
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str, llm_processor=None, scraper_name: str = "Job Crawler"):
        """
        Initialize Telegram notifier

        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID to send messages to
            llm_processor: Optional LLM processor for job descriptions
            scraper_name: Name of the active scraper to show in notifications
        """
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id
        self.llm_processor = llm_processor
        self.scraper_name = scraper_name

    async def send_job_notifications(
        self,
        jobs: List[Dict],
        max_jobs_per_message: int = 10,
        description_length: int = 800
    ):
        """
        Send job notifications to Telegram

        Args:
            jobs: List of job dictionaries
            max_jobs_per_message: Maximum jobs to include per message
            description_length: Character threshold for LLM processing
        """
        if not jobs:
            await self._send_message("🔍 No new jobs found matching your criteria today.")
            return

        sorted_jobs = sorted(jobs, key=lambda x: x.get('companyEmployeesCount') or 0, reverse=True)

        header = f"📋 *{self.scraper_name} found {len(sorted_jobs)} new job(s) in Munich*\n\n"
        await self._send_message(header)

        for i, job in enumerate(sorted_jobs, 1):
            message = await self._format_job_message(job, i, description_length)

            try:
                await self._send_message(message)

                if i % max_jobs_per_message == 0 and i < len(sorted_jobs):
                    await self._send_message(f"_Sent {i}/{len(sorted_jobs)} jobs..._")

            except Exception as e:
                logger.error(f"Error sending job {i}: {str(e)}")
                continue

        footer = f"\n✅ *Completed sending {len(sorted_jobs)} job notification(s)*"
        await self._send_message(footer)

    async def _format_job_message(self, job: Dict, index: int, desc_threshold: int) -> str:
        """Format a single job as a Telegram message"""

        title = job.get('title', 'Unknown Position')
        company = job.get('companyName', 'Unknown Company')
        location = job.get('location', 'Germany')
        posted_at_raw = job.get('postedAt', job.get('listedAt', ''))
        seniority = job.get('seniority', 'Not specified')
        employment_type = job.get('employmentType', 'Not specified')
        employee_count = job.get('companyEmployeesCount', 'Unknown')
        description_raw = job.get('descriptionText', job.get('description', 'No description available'))

        posted_at = self._format_date(posted_at_raw)

        llm_processed = False
        if self.llm_processor and self.llm_processor.should_process_with_llm(description_raw, desc_threshold):
            logger.info(f"Using LLM to process description for: {title}")
            description = self.llm_processor.process_description(job)
            llm_processed = True
        else:
            if len(description_raw) > 500:
                description = description_raw[:500] + "..."
            else:
                description = description_raw

        if not llm_processed:
            description = self._escape_markdown(description.replace('<', '').replace('>', ''))
        else:
            description = description.replace('*', '').replace('_', '')

        message = f"""
🔹 *Job {index}: {self._escape_markdown(title)}*

🏢 *Company:* {self._escape_markdown(company)}
👥 *Company Size:* {self._escape_markdown(str(employee_count))} employees
📍 *Location:* {self._escape_markdown(location)}
📅 *Posted:* {self._escape_markdown(posted_at)}
👔 *Seniority:* {self._escape_markdown(seniority)}
💼 *Type:* {self._escape_markdown(employment_type)}

📄 *Description:*
{description}
"""
        return message.strip()

    async def _send_message(self, text: str):
        """Send a message to Telegram"""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
        except TelegramError as e:
            logger.error(f"Telegram error: {str(e)}")
            try:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=text,
                    disable_web_page_preview=True
                )
            except TelegramError as e2:
                logger.error(f"Failed to send message even without markdown: {str(e2)}")
                raise

    @staticmethod
    def _format_date(date_str: str) -> str:
        """
        Format ISO date string to human-readable format

        Args:
            date_str: ISO format date string (e.g., "2026-05-31T12:09:44.000Z")

        Returns:
            Formatted date string (e.g., "May 31, 2026 at 12:09 PM")
        """
        if not date_str:
            return "Recently"

        try:
            dt = parser.parse(date_str)
            return dt.strftime("%b %d, %Y at %I:%M %p")
        except Exception as e:
            logger.warning(f"Error formatting date {date_str}: {e}")
            return date_str

    @staticmethod
    def _escape_markdown(text: str) -> str:
        """Escape special characters for Telegram MarkdownV2"""
        if not text:
            return ""

        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        escaped = str(text)

        for char in special_chars:
            escaped = escaped.replace(char, f'\\{char}')

        return escaped

    async def test_connection(self) -> bool:
        """Test if bot can send messages"""
        try:
            await self._send_message(f"✅ {self.scraper_name} connection test successful!")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
