"""
Scrape Chaumasa (Chaturmas) start and end dates from Drik Panchang.
Resumable — picks up where it left off if interrupted.

Usage:
    pip install requests beautifulsoup4
    python scrape_chaumasa.py
"""

import requests
from bs4 import BeautifulSoup
import re
import csv
import time
from pathlib import Path
from datetime import datetime

DEVSHAYANI_URL = "https://www.drikpanchang.com/ekadashis/devshayani/devshayani-ekadashi-date-time.html?year={year}"
PRABODHINI_URL = "https://www.drikpanchang.com/ekadashis/prabodhini/prabodhini-ekadashi-date-time.html?year={year}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

DATE_PATTERN = re.compile(
    r"Ekadashi\s+on\s+\w+,\s+(\w+\s+\d{1,2},\s+\d{4})"
)

OUTPUT = Path("data/chaumasa_dates.csv")
START_YEAR = 1891
END_YEAR = 2024


def scrape_date(url):
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text()
    match = DATE_PATTERN.search(text)
    if match:
        date_str = match.group(1)
        return datetime.strptime(date_str, "%B %d, %Y").strftime("%Y-%m-%d")
    return None


def load_existing():
    """Load already-scraped years from CSV."""
    existing = {}
    if OUTPUT.exists():
        with open(OUTPUT, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing[int(row["year"])] = row
    return existing


def save_all(results):
    """Write all results to CSV."""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["year", "chaumasa_start", "chaumasa_end"])
        writer.writeheader()
        for year in sorted(results.keys()):
            writer.writerow(results[year])


def main():
    existing = load_existing()
    print(f"Already scraped: {len(existing)} years")

    # Find years still needed
    remaining = [y for y in range(START_YEAR, END_YEAR + 1) if y not in existing]
    print(f"Remaining: {len(remaining)} years\n")

    if not remaining:
        print("All done!")
        return

    results = dict(existing)

    for i, year in enumerate(remaining):
        try:
            dev_date = scrape_date(DEVSHAYANI_URL.format(year=year))
            pra_date = scrape_date(PRABODHINI_URL.format(year=year))

            results[year] = {
                "year": year,
                "chaumasa_start": dev_date or "",
                "chaumasa_end": pra_date or "",
            }

            print(f"[{i+1}/{len(remaining)}] {year}: start={dev_date}, end={pra_date}")

            # Save after every year so progress is never lost
            save_all(results)

            time.sleep(1)

        except Exception as e:
            print(f"[{i+1}/{len(remaining)}] {year}: ERROR - {e}")
            print("Saving progress and stopping. Re-run to resume.")
            save_all(results)
            return

    print(f"\nDone! Saved {len(results)} rows to {OUTPUT}")

    failed = [y for y, r in results.items() if not r["chaumasa_start"] or not r["chaumasa_end"]]
    if failed:
        print(f"⚠️  Missing dates for years: {failed}")


if __name__ == "__main__":
    main()