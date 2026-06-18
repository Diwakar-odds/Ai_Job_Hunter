"""
matcher.py - Skill-based job matching engine for AI Job Hunter.

Scores jobs based on skill matches, keyword relevance, and location preference.
Uses regex word boundaries for accurate skill detection.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger('JobHunter')


class JobMatcher:
    """Matches and scores jobs against a user's skills and preferences."""

    def __init__(
        self,
        skills: list,
        keywords: list,
        location_preferences: Optional[list] = None,
    ) -> None:
        """Initialize the matcher with user skills and search keywords.

        Args:
            skills: List of the user's technical skills.
            keywords: List of job search keywords / desired job titles.
            location_preferences: Optional list of preferred locations.
        """
        self.skills = [s.lower() for s in skills]
        self.keywords = [k.lower() for k in keywords]
        self.location_preferences = [
            loc.lower() for loc in (location_preferences or [])
        ]

        # Pre-compile regex patterns for each skill (word-boundary matching)
        self._skill_patterns: list[tuple[str, re.Pattern]] = []
        for skill in self.skills:
            # Escape special regex characters in skill names (e.g. "C++", "React.js")
            escaped = re.escape(skill)
            pattern = re.compile(rf'\b{escaped}\b', re.IGNORECASE)
            self._skill_patterns.append((skill, pattern))

        # Pre-compile keyword patterns
        self._keyword_patterns: list[tuple[str, re.Pattern]] = []
        for kw in self.keywords:
            escaped = re.escape(kw)
            pattern = re.compile(rf'\b{escaped}\b', re.IGNORECASE)
            self._keyword_patterns.append((kw, pattern))

    def score_job(self, job: dict) -> tuple[float, list]:
        """Score a job based on skill matches, keyword relevance, and location.

        Scoring breakdown:
        - Skill matches: up to 70 points (proportional to matched skills)
        - Title keyword match: up to 20 points
        - Location preference match: up to 10 points

        Args:
            job: Dictionary with job data (title, description, tags, location).

        Returns:
            Tuple of (match_score 0-100, list of matched skill names).
        """
        title = job.get('title', '')
        description = job.get('description', '')
        tags = job.get('tags', '')
        location = job.get('location', '')

        # Combine text fields for skill matching
        combined_text = f'{title} {description} {tags}'

        # --- Skill matching (up to 70 points) ---
        matched_skills: list[str] = []
        for skill_name, pattern in self._skill_patterns:
            if pattern.search(combined_text):
                matched_skills.append(skill_name)

        if self.skills:
            skill_score = (len(matched_skills) / len(self.skills)) * 70
        else:
            skill_score = 0.0

        # --- Keyword/title matching (up to 20 points) ---
        keyword_score = 0.0
        title_lower = title.lower()
        keyword_hits = 0
        for kw, pattern in self._keyword_patterns:
            if pattern.search(title_lower):
                keyword_hits += 1
        if self.keywords:
            keyword_score = min((keyword_hits / max(len(self.keywords), 1)) * 40, 20)

        # --- Location matching (up to 10 points) ---
        location_score = 0.0
        if location and self.location_preferences:
            location_lower = location.lower()
            for pref in self.location_preferences:
                if pref in location_lower:
                    location_score = 10.0
                    break

        total_score = round(skill_score + keyword_score + location_score, 1)
        total_score = min(total_score, 100.0)

        return total_score, matched_skills

    def filter_jobs(self, jobs: list, min_score: float) -> list:
        """Score all jobs, filter by minimum score, and sort descending.

        Each job dict is enriched with 'match_score' and 'skills_matched' fields.

        Args:
            jobs: List of job dictionaries.
            min_score: Minimum match score (0-100) to include.

        Returns:
            Filtered and sorted list of job dictionaries.
        """
        scored_jobs: list = []

        for job in jobs:
            score, matched_skills = self.score_job(job)
            if score >= min_score:
                job['match_score'] = score
                job['skills_matched'] = ', '.join(matched_skills)
                scored_jobs.append(job)

        # Sort by score descending
        scored_jobs.sort(key=lambda j: j.get('match_score', 0), reverse=True)

        logger.info(
            f'Matcher: {len(scored_jobs)}/{len(jobs)} jobs passed '
            f'min_score={min_score}%'
        )
        return scored_jobs
