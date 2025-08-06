#!/usr/bin/env python3
"""
scarping_genre_mapping.py

Builds a mapping of main music genres to subgenres using the Wikipedia API
to fetch wikitext from the "List_of_music_genres_and_styles" page, then
parses headings and list items to produce a CSV.
"""

import sys
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import csv

# Helper to ensure each main genre appears as its own subgenre entry unless already present
def ensure_main_as_sub(df: pd.DataFrame) -> pd.DataFrame:
    """
    Append rows where main_genre == subgenre for any main_genre
    not already present as a subgenre.
    """
    mains = set(df['main_genre'].dropna().astype(str).str.strip().str.lower())
    subs  = set(df['subgenre'].dropna().astype(str).str.strip().str.lower())
    to_add = [
        {'main_genre': mg, 'subgenre': mg}
        for mg in mains
        if mg not in subs
    ]
    if to_add:
        df = pd.concat([df, pd.DataFrame(to_add)], ignore_index=True)
        df = df.drop_duplicates(subset=['main_genre','subgenre']).reset_index(drop=True)
    return df

# 1) Determine project root and output directory
try:
    script_dir = Path(__file__).resolve().parent
except NameError:
    script_dir = Path.cwd()
project_root = script_dir.parent
out_dir = project_root / "data" / "scraping" / "genre"
out_dir.mkdir(parents=True, exist_ok=True)

# 2) Fetch page wikitext via MediaWiki API
api_url = "https://en.wikipedia.org/w/api.php"
params = {
    "action": "query",
    "prop": "revisions",
    "titles": "List_of_music_genres_and_styles",
    "rvslots": "main",
    "rvprop": "content",
    "format": "json",
    "formatversion": "2"
}
resp = requests.get(api_url, params=params, timeout=10)
resp.raise_for_status()
data = resp.json()

pages = data.get("query", {}).get("pages", [])
if not pages:
    raise RuntimeError("No pages in API response")
wikitext = pages[0].get("revisions", [{}])[0].get("slots", {}).get("main", {}).get("content", "")
if not wikitext:
    raise RuntimeError("Empty wikitext content")

# 3) Parse wikitext for headings and list items
mapping = []
current_main = None
skip_sections = {"See also", "References", "External links", "Further reading", "Notes", "Bibliography"}

for line in wikitext.splitlines():
    # Match any heading (==, ===, etc.) and capture the text
    m = re.match(r"^(=+)\s*(.*?)\s*\1\s*$", line)
    if m:
        heading = m.group(2).strip()
        if heading not in skip_sections:
            current_main = heading
        else:
            current_main = None
        continue
    # When inside a valid genre section, look for list items
    if current_main and line.startswith("*"):
        item = line.lstrip("* ").strip()
        # Resolve [[Wiki|Label]] to Label
        item = re.sub(r"\[\[([^|\]]*\|)?([^\]]+)\]\]", r"\2", item)
        # Remove parenthetical extras
        item = re.sub(r"\s*\([^)]*\)", "", item).strip()
        if item:
            mapping.append({"main_genre": current_main, "subgenre": item})

# 3.5) HTML fallback for Electronic if missing from wikitext
if not any(m.get('main_genre', '').strip().lower() == 'electronic' for m in mapping):
    html = requests.get("https://en.wikipedia.org/wiki/List_of_music_genres_and_styles", timeout=10).text
    soup = BeautifulSoup(html, "html.parser")
    # Locate the HTML section for Electronic
    h3 = soup.find("h3", id="Electronic")
    if h3:
        container = h3.parent
        # Find the first div.div-col sibling
        div_col = container.find_next_sibling(lambda tag: tag.name == "div" and "div-col" in (tag.get("class") or []))
        if div_col:
            ul = div_col.find("ul")
            if ul:
                # Walk all list items (including nested) and extract the link text
                for li in ul.find_all("li"):
                    a = li.find("a")
                    if not a:
                        continue
                    text = a.get_text().strip()
                    # Remove any residual parenthetical content
                    text = re.sub(r"\s*\([^)]*\)", "", text).strip()
                    if text:
                        mapping.append({"main_genre": "Electronic", "subgenre": text})
# 3.6) HTML fallback for Hip hop if missing from wikitext
if not any(m.get('main_genre', '').strip().lower() == 'hip hop' for m in mapping):
    html = requests.get("https://en.wikipedia.org/wiki/List_of_music_genres_and_styles", timeout=10).text
    soup = BeautifulSoup(html, "html.parser")
    # Locate the HTML section for Hip hop
    h3 = soup.find("h3", id="Hip_hop")
    if h3:
        container = h3.parent
        # Find the first div.div-col sibling
        div_col = container.find_next_sibling(lambda tag: tag.name == "div" and "div-col" in (tag.get("class") or []))
        if div_col:
            ul = div_col.find("ul")
            if ul:
                # Walk all list items (including nested) and extract the link or text
                for li in ul.find_all("li"):
                    # Prefer anchor text if present
                    a = li.find("a")
                    text = a.get_text().strip() if a else li.get_text().strip()
                    # Remove any residual parenthetical content
                    text = re.sub(r"\s*\([^)]*\)", "", text).strip()
                    if text:
                        mapping.append({"main_genre": "Hip hop", "subgenre": text})
                        
# 4) Convert to DataFrame, dedupe and clean
df_mapping = pd.DataFrame(mapping).drop_duplicates().reset_index(drop=True)
df_mapping['main_genre'] = (
    df_mapping['main_genre']
      .str.replace(r'^=+\s*', '', regex=True)   # remove leading '=' characters
      .str.replace(r'\s*=+$', '', regex=True)   # remove trailing '=' characters
      .str.strip()                              # trim any leftover whitespace
)


# 4.5) Ensure each main genre appears as its own subgenre entry
df_mapping = ensure_main_as_sub(df_mapping)

# 5) Save mapping to CSV
out_path = out_dir / "genre_mapping.csv"
df_mapping.to_csv(out_path, index=False, quoting=csv.QUOTE_ALL)
print(f"Saved genre->subgenre mapping to {out_path}")
