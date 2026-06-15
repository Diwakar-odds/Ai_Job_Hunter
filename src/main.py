"""
main.py - Main orchestrator for the AI Job Hunter agent.

Coordinates scraping, matching, database storage, Telegram notifications,
and dashboard data export.
"""

import yaml
import os
import sys
import json
import logging
import time
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent.resolve()
DATA_DIR = ROOT / 'data'
DATA_DIR.mkdir(exist_ok=True)
DASHBOARD_DATA = ROOT / 'dashboard' / 'data.js'

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(DATA_DIR / 'job_hunter.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger('JobHunter')


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------
def load_config() -> dict:
    """Load configuration from config.yaml.

    Returns:
        Parsed configuration dictionary.
    """
    config_path = ROOT / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_config(config: dict) -> None:
    """Persist the configuration back to config.yaml.

    Args:
        config: Configuration dictionary to save.
    """
    config_path = ROOT / 'config.yaml'
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


# ---------------------------------------------------------------------------
# Dashboard export
# ---------------------------------------------------------------------------
def update_dashboard(db) -> None:
    """Export jobs data as a JS file consumed by the dashboard.

    Args:
        db: JobDatabase instance.
    """
    try:
        jobs_json = db.export_for_dashboard()
        DASHBOARD_DATA.parent.mkdir(parents=True, exist_ok=True)
        with open(DASHBOARD_DATA, 'w', encoding='utf-8') as f:
            f.write(f'const JOBS_DATA = {jobs_json};\n')
            f.write(f'const LAST_UPDATED = "{datetime.now().isoformat()}";\n')
        logger.info(f'Dashboard data updated: {len(json.loads(jobs_json))} jobs')
    except Exception as e:
        logger.error(f'Failed to update dashboard: {e}')


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------
def run() -> None:
    """Execute one full cycle of the job hunting pipeline."""
    try:
        logger.info('=' * 50)
        logger.info('🚀 AI Job Hunter - Starting search...')
        logger.info('=' * 50)

        config = load_config()

        # ------------------------------------------------------------------
        # Initialize components
        # ------------------------------------------------------------------
        from database import JobDatabase
        from scrapers import run_all_scrapers
        from matcher import JobMatcher
        from notifier import TelegramNotifier

        db = JobDatabase(str(DATA_DIR / 'jobs.db'))
        matcher = JobMatcher(
            skills=config['search']['skills'],
            keywords=config['search']['keywords'],
            location_preferences=config['search'].get('location_preferences'),
        )
        notifier = TelegramNotifier(
            bot_token=config['telegram']['bot_token'],
            chat_id=config['telegram'].get('chat_id') or None,
        )

        # ------------------------------------------------------------------
        # Step 1: Scrape jobs
        # ------------------------------------------------------------------
        logger.info('📡 Scraping job boards...')
        raw_jobs = run_all_scrapers(config['search']['keywords'])
        logger.info(f'Found {len(raw_jobs)} raw jobs across all sources')

        # ------------------------------------------------------------------
        # Step 2: Match and score
        # ------------------------------------------------------------------
        logger.info('🎯 Scoring job matches...')
        min_score = config['search'].get('min_match_score', 40)
        matched_jobs = matcher.filter_jobs(raw_jobs, min_score)
        logger.info(
            f'{len(matched_jobs)} jobs passed minimum match score of {min_score}%'
        )

        # ------------------------------------------------------------------
        # Step 3: Save to database
        # ------------------------------------------------------------------
        new_count = 0
        for job in matched_jobs:
            if db.add_job(job):
                new_count += 1

        logger.info(f'💾 {new_count} NEW jobs saved to database')

        # Log search activity
        db.log_search(
            source='all',
            found=len(raw_jobs),
            new=new_count,
        )

        # ------------------------------------------------------------------
        # Step 4: Notify via Telegram
        # ------------------------------------------------------------------
        if new_count > 0:
            new_jobs = db.get_new_jobs()
            logger.info(
                f'📱 Sending {len(new_jobs)} notifications via Telegram...'
            )
            notifier.notify_new_jobs(new_jobs)
            # Mark as notified
            db.mark_as_notified([j['id'] for j in new_jobs])
        else:
            logger.info('No new jobs to notify about.')

        # ------------------------------------------------------------------
        # Step 5: Update dashboard
        # ------------------------------------------------------------------
        update_dashboard(db)

        # ------------------------------------------------------------------
        # Step 6: Log stats
        # ------------------------------------------------------------------
        stats = db.get_stats()
        logger.info(f'📊 Stats: {stats}')
        logger.info('✅ Search complete!')

        # ------------------------------------------------------------------
        # Auto-save chat_id if newly detected
        # ------------------------------------------------------------------
        if notifier.chat_id and not config['telegram'].get('chat_id'):
            config['telegram']['chat_id'] = notifier.chat_id
            save_config(config)
            logger.info('💬 Auto-saved Telegram chat_id to config')

    except FileNotFoundError as e:
        logger.error(f'Configuration file not found: {e}')
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f'Invalid YAML in config file: {e}')
        sys.exit(1)
    except KeyError as e:
        logger.error(f'Missing required config key: {e}')
        sys.exit(1)
    except Exception as e:
        logger.error(f'Unexpected error during job hunt: {e}', exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    run()
