"""
notifier.py - Telegram notification sender for AI Job Hunter.

Sends formatted job match alerts and daily summaries via Telegram Bot API.
Auto-detects chat_id from the latest message if not configured.
"""

import logging
from typing import Optional

import requests

logger = logging.getLogger('JobHunter')

TELEGRAM_API_BASE = 'https://api.telegram.org/bot{token}'
REQUEST_TIMEOUT = 15


class TelegramNotifier:
    """Sends job notifications and summaries via Telegram."""

    def __init__(self, bot_token: str, chat_id: Optional[str] = None) -> None:
        """Initialize the Telegram notifier.

        Args:
            bot_token: Telegram Bot API token from @BotFather.
            chat_id: Target chat ID. If empty/None, will be auto-detected.
        """
        self.bot_token = bot_token
        self.chat_id = chat_id if chat_id else None
        self._is_placeholder = (
            not bot_token or bot_token == 'YOUR_BOT_TOKEN_HERE'
        )

        if self._is_placeholder:
            logger.warning(
                '⚠️  Telegram bot_token is not configured. '
                'Notifications will be skipped. '
                'Get a token from @BotFather on Telegram and update config.yaml'
            )
        elif not self.chat_id:
            self.chat_id = self._get_chat_id()

    def _get_chat_id(self) -> Optional[str]:
        """Auto-detect chat_id from the latest message sent to the bot.

        Returns:
            The chat ID string, or None if detection fails.
        """
        if self._is_placeholder:
            return None

        url = f'{TELEGRAM_API_BASE.format(token=self.bot_token)}/getUpdates'
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if not data.get('ok') or not data.get('result'):
                logger.warning(
                    'No messages found. Send any message to your bot first, '
                    'then restart.'
                )
                return None

            # Get the chat_id from the latest update
            latest_update = data['result'][-1]
            message = latest_update.get('message', latest_update.get('channel_post', {}))
            chat_id = str(message.get('chat', {}).get('id', ''))

            if chat_id:
                logger.info(f'Auto-detected Telegram chat_id: {chat_id}')
                return chat_id
            else:
                logger.warning('Could not extract chat_id from updates.')
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to get Telegram updates: {e}')
            return None

    def send_message(self, text: str, parse_mode: str = 'HTML') -> bool:
        """Send a message via Telegram Bot API.

        Args:
            text: The message text to send.
            parse_mode: Message parse mode ('HTML' or 'Markdown').

        Returns:
            True if the message was sent successfully, False otherwise.
        """
        if self._is_placeholder:
            logger.debug('Skipping Telegram message (no token configured).')
            return False

        if not self.chat_id:
            logger.warning('No chat_id available. Cannot send message.')
            return False

        url = f'{TELEGRAM_API_BASE.format(token=self.bot_token)}/sendMessage'
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True,
        }

        try:
            response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            result = response.json()

            if result.get('ok'):
                logger.debug('Telegram message sent successfully.')
                return True
            else:
                logger.warning(f'Telegram API error: {result.get("description", "Unknown")}')
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to send Telegram message: {e}')
            return False

    def notify_new_jobs(self, jobs: list) -> None:
        """Send formatted notifications for new job matches.

        Sends at most 10 jobs per batch to avoid flooding.

        Args:
            jobs: List of job dictionaries to notify about.
        """
        if self._is_placeholder:
            logger.info(
                f'[DRY RUN] Would notify about {len(jobs)} jobs '
                '(Telegram not configured)'
            )
            return

        batch = jobs[:10]  # Max 10 per batch
        for job in batch:
            title = _escape_html(job.get('title', 'Unknown'))
            company = _escape_html(job.get('company', 'Unknown'))
            location = _escape_html(job.get('location', 'N/A'))
            score = job.get('match_score', 0)
            skills = _escape_html(job.get('skills_matched', 'N/A'))
            url = job.get('url', '')

            message = (
                f'🔔 <b>New Job Match!</b>\n'
                f'\n'
                f'💼 <b>{title}</b>\n'
                f'🏢 {company}\n'
                f'📍 {location}\n'
                f'📊 Match: <b>{score}%</b>\n'
                f'🎯 Skills: {skills}\n'
                f'\n'
                f'🔗 <a href="{url}">Apply Here</a>'
            )

            success = self.send_message(message)
            if not success:
                logger.warning(f'Failed to notify about job: {title}')

        if len(jobs) > 10:
            remaining = len(jobs) - 10
            self.send_message(
                f'📋 ... and <b>{remaining}</b> more jobs. '
                f'Check the dashboard for the full list!'
            )

    def send_summary(self, stats: dict) -> None:
        """Send a daily summary of job search statistics.

        Args:
            stats: Dictionary with status counts (e.g., new, viewed, applied, total).
        """
        if self._is_placeholder:
            logger.info('[DRY RUN] Would send summary (Telegram not configured)')
            return

        total = stats.get('total', 0)
        new = stats.get('new', 0)
        viewed = stats.get('viewed', 0)
        applied = stats.get('applied', 0)
        rejected = stats.get('rejected', 0)

        message = (
            f'📊 <b>Job Hunter Daily Summary</b>\n'
            f'\n'
            f'📦 Total Jobs: <b>{total}</b>\n'
            f'🆕 New: <b>{new}</b>\n'
            f'👀 Viewed: <b>{viewed}</b>\n'
            f'✅ Applied: <b>{applied}</b>\n'
            f'❌ Rejected: <b>{rejected}</b>\n'
            f'\n'
            f'Keep going! 💪'
        )

        self.send_message(message)


def _escape_html(text: str) -> str:
    """Escape HTML special characters for Telegram HTML parse mode.

    Args:
        text: Raw text string.

    Returns:
        HTML-escaped string.
    """
    return (
        text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )
