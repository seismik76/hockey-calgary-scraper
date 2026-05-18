"""
Retry standings URLs that failed during the last scrape.

Reads `scrape_log.txt` (or any log file) for lines like:
    Error fetching <URL>: ...

For each unique URL matching the standings pattern, this script:
  1. Resolves it to (Season, League, type) via the DB
  2. Re-fetches with extended retries and a longer timeout
  3. Parses standings and writes via save_standings

Use when a one-shot scrape hits transient upstream timeouts and you don't want
to re-run the whole 30+ minute sync just to plug a handful of holes.

Usage:
    python scripts/maintenance/retry_failed_fetches.py
    python scripts/maintenance/retry_failed_fetches.py --log-file scrape_log.txt --dry-run
"""
import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bs4 import BeautifulSoup

from database import SessionLocal
from models import Season, League
from scraper import SESSION, parse_standings, save_standings, BASE_URL
from utilities.utils import load_community_map


STANDINGS_URL_RE = re.compile(
    r'https://www\.hockeycalgary\.ca'
    r'/standings/index/stream/(?P<stream>[^/]+)'
    r'/league/(?P<slug>[^/]+)'
    r'/season/(?P<season>[^/]+)'
    r'(?:/type/(?P<type>[^/\s:]+))?'
)

URL_TYPE_TO_LEAGUE_TYPE = {
    'league': 'Regular',
    'seeding': 'Seeding',
    'playoff': 'Playoff',
    'tournament': 'Tournament',
    None: 'Regular',
}


def extract_failed_urls(log_path: Path):
    """Pull standings URLs out of 'Error fetching <URL>:' lines."""
    urls = []
    seen = set()
    if not log_path.exists():
        return urls
    text = log_path.read_text(encoding='utf-8', errors='replace')
    # Match the URL up to ": " (colon+space) — the colon inside https:// is followed
    # by '/', not whitespace, so non-greedy + lookahead avoids stopping there.
    for match in re.finditer(r'Error fetching (\S+?):\s', text):
        url = match.group(1)
        m = STANDINGS_URL_RE.match(url)
        if not m:
            continue
        if url in seen:
            continue
        seen.add(url)
        urls.append((url, m.groupdict()))
    return urls


def patient_fetch(url, attempts=5, base_sleep=2):
    """Fetch with exponential backoff. Returns parsed soup or None."""
    for i in range(attempts):
        try:
            r = SESSION.get(url, timeout=(10, 60))
            r.raise_for_status()
            return BeautifulSoup(r.content, 'html.parser')
        except Exception as e:
            wait = base_sleep * (2 ** i)
            print(f"    attempt {i+1}/{attempts} failed ({type(e).__name__}); sleeping {wait}s")
            if i < attempts - 1:
                time.sleep(wait)
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log-file', default='scrape_log.txt')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    log_path = Path(args.log_file).resolve()
    print(f"Log: {log_path}")
    urls = extract_failed_urls(log_path)
    print(f"Found {len(urls)} unique failed standings URLs.")
    if not urls:
        return

    community_map = load_community_map()
    db = SessionLocal()
    stats = {'recovered': 0, 'still_failing': 0, 'no_db_match': 0, 'empty_after_retry': 0}

    try:
        for url, parts in urls:
            stream = parts['stream']
            slug = parts['slug']
            season_name = parts['season']
            league_type = URL_TYPE_TO_LEAGUE_TYPE.get(parts['type'], 'Regular')

            print(f"\n  {url}")
            print(f"    -> stream={stream} slug={slug} season={season_name} type={league_type}")

            season = db.query(Season).filter_by(name=season_name).first()
            league = db.query(League).filter_by(slug=slug, stream=stream, type=league_type).first()
            if not (season and league):
                print(f"    no DB match (season={season is not None}, league={league is not None})")
                stats['no_db_match'] += 1
                continue

            if args.dry_run:
                print(f"    [dry-run] would refetch {url}")
                continue

            soup = patient_fetch(url)
            if not soup:
                stats['still_failing'] += 1
                continue

            data = parse_standings(soup)
            if not data:
                print(f"    parsed 0 rows (page exists but no standings)")
                stats['empty_after_retry'] += 1
                continue

            print(f"    recovered {len(data)} standings rows")
            save_standings(db, data, season, league, community_map, url)
            stats['recovered'] += 1
    finally:
        db.close()

    print()
    print("Summary:")
    for k, v in stats.items():
        print(f"  {k:<25} {v:>4}")


if __name__ == '__main__':
    main()
