import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import csv

def scrape_genre_from_wiki(url: str) -> list[str]:
    # 1) Download the page
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # 2) Find the infobox
    infobox = soup.find("table", class_="infobox")
    if not infobox:
        return []

    # 3) Locate the Genre row
    for row in infobox.find_all("tr"):
        th = row.find("th")
        if th and "Genre" in th.get_text():
            td = row.find("td")
            if not td:
                return []
            # 4a) If it’s a list (<ul> or <div class="plainlist">), grab each <li>
            lst = td.find(["ul", "div"], class_="plainlist")
            if lst:
                return [li.get_text(strip=True) for li in lst.find_all("li")]

            # 4b) Otherwise fall back to comma-separated text
            text = td.get_text(separator=",").strip()
            return [g.strip() for g in text.split(",") if g.strip()]

    return []

if __name__ == "__main__":
    # 1) Determine project root and data path
    project_root = Path(__file__).resolve().parent.parent
    raw_path = project_root / "data" / "raw" / "neo4j_artists.csv"

    # 2) Load artist data and filter to those with wiki_url
    # Read CSV in Python engine and skip bad lines
    df_art = pd.read_csv(
        raw_path,
        dtype=str,
        engine='python',
        on_bad_lines='skip'
    )
    df_art = df_art[df_art["wiki_url"].notna() & df_art["wiki_url"].str.strip().astype(bool)]

    # Prepare to collect results
    results = []

    # 3) For each artist, scrape, print, and collect genres
    for _, row in df_art.iterrows():
        artist_id = row["artist_id"]
        name = row.get("common_name", "")
        url = row["wiki_url"]
        print(f"Artist: {name} ({artist_id})")

        # Fail-safe: skip artists with broken URLs
        try:
            genres = scrape_genre_from_wiki(url)
        except Exception as e:
            print(f"  ! Skipped {name} ({artist_id}) - error fetching URL: {e}")
            continue

        print("  Genres:", genres)
        results.append({
            "artist_id": artist_id,
            "common_name": name,
            "wiki_url": url,
            "genres": "|".join(genres)  # join by pipe to keep CSV cells clean
        })

    # 4) Save collected genres to CSV
    out_dir = project_root / "data" / "scraping" / "genre"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "artist_genres_raw.csv"
    # Save with full quoting to protect commas in fields
    pd.DataFrame(results).to_csv(
        out_path,
        index=False,
        quoting=csv.QUOTE_ALL
    )
    print(f"Saved genres to {out_path}")