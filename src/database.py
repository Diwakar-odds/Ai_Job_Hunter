"""
database.py - SQLite database manager for AI Job Hunter.

Manages job storage, status tracking, search logging, and dashboard export.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger('JobHunter')


class JobDatabase:
    """SQLite database manager for job listings and search activity."""

    def __init__(self, db_path: str) -> None:
        """Initialize the database, creating tables if they don't exist.

        Args:
            db_path: Absolute or relative path to the SQLite database file.
        """
        self.db_path = db_path
        # Ensure parent directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._create_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """Create and return a new database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self) -> None:
        """Create the jobs and search_log tables if they don't exist."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS jobs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT,
                        company TEXT,
                        location TEXT,
                        url TEXT UNIQUE,
                        description TEXT,
                        source TEXT,
                        tags TEXT,
                        match_score REAL,
                        skills_matched TEXT,
                        posted_date TEXT,
                        found_date TEXT DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'new',
                        applied_date TEXT
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS search_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        search_time TEXT DEFAULT CURRENT_TIMESTAMP,
                        source TEXT,
                        jobs_found INTEGER,
                        new_jobs INTEGER
                    )
                ''')
                conn.commit()
                logger.info('Database tables initialized.')
        except sqlite3.Error as e:
            logger.error(f'Failed to create database tables: {e}')
            raise

    def add_job(self, job_data: dict) -> bool:
        """Add a job to the database.

        Args:
            job_data: Dictionary containing job fields (title, company,
                      location, url, description, source, tags, match_score,
                      skills_matched, posted_date).

        Returns:
            True if the job was inserted, False if the URL already exists.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO jobs (title, company, location, url, description,
                                     source, tags, match_score, skills_matched,
                                     posted_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    job_data.get('title', ''),
                    job_data.get('company', ''),
                    job_data.get('location', ''),
                    job_data.get('url', ''),
                    job_data.get('description', ''),
                    job_data.get('source', ''),
                    job_data.get('tags', ''),
                    job_data.get('match_score', 0.0),
                    job_data.get('skills_matched', ''),
                    job_data.get('posted_date', ''),
                ))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            # URL already exists
            logger.debug(f'Duplicate job URL skipped: {job_data.get("url", "")}')
            return False
        except sqlite3.Error as e:
            logger.error(f'Failed to add job: {e}')
            return False

    def get_new_jobs(self) -> list:
        """Return all jobs with status 'new'.

        Returns:
            List of job dictionaries.
        """
        return self.get_all_jobs(status='new')

    def get_all_jobs(self, status: Optional[str] = None) -> list:
        """Return jobs, optionally filtered by status.

        Args:
            status: Filter by this status value. If None, returns all jobs.

        Returns:
            List of job dictionaries.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if status:
                    cursor.execute(
                        'SELECT * FROM jobs WHERE status = ? ORDER BY found_date DESC',
                        (status,)
                    )
                else:
                    cursor.execute('SELECT * FROM jobs ORDER BY found_date DESC')
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f'Failed to fetch jobs: {e}')
            return []

    def update_status(self, job_id: int, status: str) -> None:
        """Update the status of a job.

        Args:
            job_id: The database ID of the job.
            status: New status value (new/viewed/applied/rejected).
        """
        valid_statuses = {'new', 'viewed', 'applied', 'rejected'}
        if status not in valid_statuses:
            logger.warning(f'Invalid status "{status}". Must be one of {valid_statuses}.')
            return
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if status == 'applied':
                    cursor.execute(
                        'UPDATE jobs SET status = ?, applied_date = CURRENT_TIMESTAMP WHERE id = ?',
                        (status, job_id)
                    )
                else:
                    cursor.execute(
                        'UPDATE jobs SET status = ? WHERE id = ?',
                        (status, job_id)
                    )
                conn.commit()
                logger.debug(f'Job {job_id} status updated to "{status}".')
        except sqlite3.Error as e:
            logger.error(f'Failed to update job {job_id} status: {e}')

    def get_stats(self) -> dict:
        """Return a count of jobs grouped by status.

        Returns:
            Dictionary mapping status strings to their counts.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT status, COUNT(*) as count FROM jobs GROUP BY status'
                )
                rows = cursor.fetchall()
                stats = {row['status']: row['count'] for row in rows}
                cursor.execute('SELECT COUNT(*) as total FROM jobs')
                stats['total'] = cursor.fetchone()['total']
                return stats
        except sqlite3.Error as e:
            logger.error(f'Failed to get stats: {e}')
            return {}

    def log_search(self, source: str, found: int, new: int) -> None:
        """Log a search activity.

        Args:
            source: The source/scraper name.
            found: Total number of jobs found.
            new: Number of new (previously unseen) jobs.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO search_log (source, jobs_found, new_jobs) VALUES (?, ?, ?)',
                    (source, found, new)
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f'Failed to log search: {e}')

    def mark_as_notified(self, job_ids: list) -> None:
        """Mark a list of jobs as 'viewed' (notified).

        Args:
            job_ids: List of job database IDs to mark.
        """
        if not job_ids:
            return
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                placeholders = ','.join('?' for _ in job_ids)
                cursor.execute(
                    f"UPDATE jobs SET status = 'viewed' WHERE id IN ({placeholders})",
                    job_ids
                )
                conn.commit()
                logger.info(f'Marked {len(job_ids)} jobs as notified/viewed.')
        except sqlite3.Error as e:
            logger.error(f'Failed to mark jobs as notified: {e}')

    def export_for_dashboard(self) -> str:
        """Export all jobs as a JSON string for the dashboard.

        Returns:
            JSON string of all job records.
        """
        try:
            jobs = self.get_all_jobs()
            return json.dumps(jobs, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            logger.error(f'Failed to export dashboard data: {e}')
            return '[]'
