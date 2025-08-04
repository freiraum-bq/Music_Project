#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import re
import csv
import os

# Header line that denotes the start of each week block
HEADER = "TW LW TITLE –•– Artist (Label)-Weeks on Chart (Peak To Date)"

# Regex pattern to match each chart entry
PATTERN = re.compile(
    r"^(?P<TW>\d+)\s+"
    r"(?P<LW>\d+)\s+"
    r"(?P<TITLE>.*?)\s+–•–\s+"
    r"(?P<ARTIST>.*?)\s*"
    r"\((?P<LABEL>[^)]+)\)-"
    r"(?P<WEEKS_ON_CHART>\d+)"
    r"(?:\s*\((?P<WEEKS_AT_1>\d+\s*week[s]? at #1)\))?\s*"
    r"\((?P<PEAK_POSITION>\d+)\)$"
)

# Determine project root (parent of this script's directory)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
# Directory where all CSV files will be saved
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'data', 'scraping', 'top40_all_years')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def scrape_year(year: int):
    """Scrape all weekly charts for a given year and write to CSV."""
    url = f"https://top40weekly.com/{year}-all-charts/"
    print(f"Scraping year {year} at {url}")
    resp = requests.get(url)
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        print(f"Failed to fetch {url}: {e}")
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    content = soup.find("div", class_="entry-content")
    if not content:
        print(f"No content found for year {year}")
        return

    lines = content.get_text("\n", strip=True).split("\n")
    # We'll count a new week whenever the header line appears
    week_count = 0
    rows = []

    for line in lines:
        text = line.strip()
        # Detect the header that starts a week block
        if text == HEADER:
            week_count += 1
            continue  # Move to the next line; entries follow the header

        # Ignore any lines that appear before the first header
        if week_count == 0:
            continue

        # Attempt to match a chart entry
        m = PATTERN.match(text)
        if not m:
            continue  # Skip anything that isn't a chart line (e.g., Power Plays)

        d = m.groupdict()
        rows.append({
            "YEAR": year,
            "WEEK": week_count,
            "TW": int(d["TW"]),
            "LW": int(d["LW"]),
            "TITLE": d["TITLE"],
            "ARTIST": d["ARTIST"],
            "LABEL": d["LABEL"],
            "WEEKS_ON_CHART": int(d["WEEKS_ON_CHART"]),
            "PEAK_POSITION": int(d["PEAK_POSITION"]),
            "WEEKS_AT_1": d.get("WEEKS_AT_1") or ""
        })

    if not rows:
        print(f"No data extracted for year {year}")
        return

    # Save each year’s CSV inside the OUTPUT_DIR
    out_file = os.path.join(OUTPUT_DIR, f"{year}_top40_allweeks.csv")
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "YEAR","WEEK","TW","LW","TITLE","ARTIST",
                "LABEL","WEEKS_ON_CHART","PEAK_POSITION","WEEKS_AT_1"
            ]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {len(rows)} entries for year {year} to {out_file}")

# %%
def merge_all_years():
    """Merge all per-year CSVs in OUTPUT_DIR into a single CSV."""
    import glob
    import pandas as pd

    pattern = os.path.join(OUTPUT_DIR, '*_top40_allweeks.csv')
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"No CSV files found in {OUTPUT_DIR} to merge.")
        return
    df_list = [pd.read_csv(fp) for fp in files]
    merged = pd.concat(df_list, ignore_index=True)
    out_file = os.path.join(OUTPUT_DIR, 'top40_all_years_merged.csv')
    merged.to_csv(out_file, index=False)
    print(f"Merged {len(files)} files into {out_file}")


def main():
    for year in range(1960, 2021):
        scrape_year(year)
    # After all years are scraped, merge them
    merge_all_years()

if __name__ == '__main__':
    main()