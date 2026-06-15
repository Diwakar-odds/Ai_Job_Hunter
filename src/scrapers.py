"""
scrapers.py - Job scrapers for free job board APIs.

Fetches job listings from RemoteOK, Arbeitnow, Jobicy, and FindWork.
Each scraper normalizes results into a consistent dictionary format.
"""

import time
import logging
from typing import Optional

import requests

logger = logging.getLogger('JobHunter')

# Common headers to identify ourselves politely
HEADERS = {
    'User-Agent': 'AI-Job-Hunter/1.0 (Python; automated job search)',
    'Accept': 'application/json',
}

REQUEST_TIMEOUT = 10  # seconds
POLITE_DELAY = 2      # seconds between requests


def _safe_get(url: str, params: Optional[dict] = None) -> Optional[requests.Response]:
    """Make a safe GET request with timeout and error handling.

    Args:
        url: The URL to fetch.
        params: Optional query parameters.

    Returns:
        Response object on success, None on failure.
    """
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response
    except requests.exceptions.Timeout:
        logger.warning(f'Timeout fetching {url}')
    except requests.exceptions.ConnectionError:
        logger.warning(f'Connection error fetching {url}')
    except requests.exceptions.HTTPError as e:
        logger.warning(f'HTTP error fetching {url}: {e}')
    except requests.exceptions.RequestException as e:
        logger.warning(f'Request error fetching {url}: {e}')
    return None


def _matches_keywords(text: str, keywords: list) -> bool:
    """Check if any keyword appears in the text (case-insensitive).

    Args:
        text: The text to search in.
        keywords: List of keyword strings.

    Returns:
        True if any keyword is found in the text.
    """
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def scrape_remoteok(keywords: list) -> list:
    """Scrape jobs from RemoteOK API.

    Args:
        keywords: List of search keyword strings.

    Returns:
        List of normalized job dictionaries.
    """
    logger.info('Scraping RemoteOK...')
    jobs = []
    response = _safe_get('https://remoteok.com/api')
    if not response:
        return jobs

    try:
        data = response.json()
        # First element is metadata, skip it
        listings = data[1:] if isinstance(data, list) and len(data) > 1 else []

        for item in listings:
            title = item.get('position', '')
            company = item.get('company', '')
            description = item.get('description', '')
            tags_list = item.get('tags', [])
            tags_str = ', '.join(tags_list) if isinstance(tags_list, list) else str(tags_list)

            # Filter: only include if job matches any keyword
            combined_text = f'{title} {company} {description} {tags_str}'
            if not _matches_keywords(combined_text, keywords):
                continue

            jobs.append({
                'title': title,
                'company': company,
                'location': item.get('location', 'Remote'),
                'url': item.get('url', ''),
                'description': description[:2000],  # Truncate long descriptions
                'source': 'RemoteOK',
                'tags': tags_str,
                'posted_date': item.get('date', ''),
            })
    except (ValueError, KeyError, IndexError) as e:
        logger.warning(f'Error parsing RemoteOK response: {e}')

    logger.info(f'RemoteOK: found {len(jobs)} matching jobs')
    return jobs


def scrape_arbeitnow(keywords: list) -> list:
    """Scrape jobs from Arbeitnow API.

    Args:
        keywords: List of search keyword strings.

    Returns:
        List of normalized job dictionaries.
    """
    logger.info('Scraping Arbeitnow...')
    time.sleep(POLITE_DELAY)
    jobs = []
    response = _safe_get('https://www.arbeitnow.com/api/job-board-api')
    if not response:
        return jobs

    try:
        data = response.json()
        listings = data.get('data', [])

        for item in listings:
            title = item.get('title', '')
            company = item.get('company_name', '')
            description = item.get('description', '')
            tags_list = item.get('tags', [])
            tags_str = ', '.join(tags_list) if isinstance(tags_list, list) else str(tags_list)

            combined_text = f'{title} {company} {description} {tags_str}'
            if not _matches_keywords(combined_text, keywords):
                continue

            jobs.append({
                'title': title,
                'company': company,
                'location': item.get('location', ''),
                'url': item.get('url', ''),
                'description': description[:2000],
                'source': 'Arbeitnow',
                'tags': tags_str,
                'posted_date': item.get('created_at', ''),
            })
    except (ValueError, KeyError) as e:
        logger.warning(f'Error parsing Arbeitnow response: {e}')

    logger.info(f'Arbeitnow: found {len(jobs)} matching jobs')
    return jobs


def scrape_jobicy(keywords: list) -> list:
    """Scrape jobs from Jobicy API.

    Args:
        keywords: List of search keyword strings.

    Returns:
        List of normalized job dictionaries.
    """
    logger.info('Scraping Jobicy...')
    time.sleep(POLITE_DELAY)
    jobs = []
    response = _safe_get('https://jobicy.com/api/v2/remote-jobs', params={'count': 50})
    if not response:
        return jobs

    try:
        data = response.json()
        listings = data.get('jobs', [])

        for item in listings:
            title = item.get('jobTitle', '')
            company = item.get('companyName', '')
            description = item.get('jobDescription', '')
            job_type = item.get('jobType', '')
            geo = item.get('jobGeo', '')

            combined_text = f'{title} {company} {description} {job_type}'
            if not _matches_keywords(combined_text, keywords):
                continue

            jobs.append({
                'title': title,
                'company': company,
                'location': geo if geo else 'Remote',
                'url': item.get('url', ''),
                'description': description[:2000],
                'source': 'Jobicy',
                'tags': job_type,
                'posted_date': item.get('pubDate', ''),
            })
    except (ValueError, KeyError) as e:
        logger.warning(f'Error parsing Jobicy response: {e}')

    logger.info(f'Jobicy: found {len(jobs)} matching jobs')
    return jobs


def scrape_findwork(keywords: list) -> list:
    """Scrape jobs from FindWork API, searching by each keyword.

    Args:
        keywords: List of search keyword strings.

    Returns:
        List of normalized job dictionaries.
    """
    logger.info('Scraping FindWork...')
    jobs = []
    seen_urls: set = set()

    for keyword in keywords:
        time.sleep(POLITE_DELAY)
        response = _safe_get(
            'https://findwork.dev/api/jobs/',
            params={'search': keyword}
        )
        if not response:
            continue

        try:
            data = response.json()
            listings = data.get('results', [])

            for item in listings:
                url = item.get('url', '')
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                title = item.get('role', '')
                company = item.get('company_name', '')
                description = item.get('text', '')
                keywords_list = item.get('keywords', [])
                tags_str = ', '.join(keywords_list) if isinstance(keywords_list, list) else ''

                jobs.append({
                    'title': title,
                    'company': company,
                    'location': item.get('location', 'Remote'),
                    'url': url,
                    'description': description[:2000],
                    'source': 'FindWork',
                    'tags': tags_str,
                    'posted_date': item.get('date_posted', ''),
                })
        except (ValueError, KeyError) as e:
            logger.warning(f'Error parsing FindWork response for "{keyword}": {e}')

    logger.info(f'FindWork: found {len(jobs)} matching jobs')
    return jobs


def run_all_scrapers(keywords: list) -> list:
    """Run all scrapers and return combined results.

    Args:
        keywords: List of search keyword strings.

    Returns:
        Combined list of normalized job dictionaries from all sources.
    """
    all_jobs: list = []

    scrapers = [
        ('RemoteOK', scrape_remoteok),
        ('Arbeitnow', scrape_arbeitnow),
        ('Jobicy', scrape_jobicy),
        ('FindWork', scrape_findwork),
    ]

    for name, scraper_fn in scrapers:
        try:
            jobs = scraper_fn(keywords)
            all_jobs.extend(jobs)
            logger.info(f'{name} contributed {len(jobs)} jobs')
        except Exception as e:
            logger.error(f'Unexpected error in {name} scraper: {e}')

    # Deduplicate by URL
    seen_urls: set = set()
    unique_jobs: list = []
    for job in all_jobs:
        url = job.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_jobs.append(job)

    logger.info(f'Total unique jobs after deduplication: {len(unique_jobs)}')
    return unique_jobs
