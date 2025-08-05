#!/usr/bin/env python3
"""
cleaning_genre.py

Processes the scraped artist_genres.csv to produce both
wide-format and exploded long-format genre tables.
"""

import sys
import os
from pathlib import Path

# 1) Set project root (parent of this script's directory)
try:
    script_dir = Path(__file__).resolve().parent
except NameError:
    script_dir = Path.cwd()
project_root = script_dir.parent
if not (project_root / "data").is_dir():
    raise RuntimeError(f"Project root {project_root!r} has no data/ folder.")
sys.path.insert(0, str(project_root))

import pandas as pd
import re
import csv

# 2) Load scraped genres
raw_path = project_root / "data" / "scraping" / "genre" / "artist_genres_raw.csv"
df = pd.read_csv(raw_path, dtype=str, keep_default_na=False)

# 3) Clean numeric artifacts like [|1|], [|2|], etc.
df['genres_clean'] = df['genres'].str.replace(r'\[\|\d+\|\]', '', regex=True)

# 4) Split on pipe into lists
df['genre_list'] = df['genres_clean'].str.split('|')

# 5) Determine max genres per artist
max_genres = int(df['genre_list'].apply(lambda lst: len(lst) if isinstance(lst, list) else 0).max())

# 6) Create wide-format columns genre_1 ... genre_N
for idx in range(max_genres):
    col = f'genre_{idx+1}'
    df[col] = df['genre_list'].apply(
        lambda lst: lst[idx].strip().lower() if isinstance(lst, list) and idx < len(lst) else ''
    )

# 7) Save wide-format table
out_dir = project_root / "data" / "scraping" / "genre"
out_dir.mkdir(parents=True, exist_ok=True)
wide_path = out_dir / "artist_genres_clean.csv"
df.to_csv(wide_path, index=False, quoting=csv.QUOTE_ALL)
print(f"Saved wide-format genres to {wide_path}")

# 8) Build exploded long-format DataFrame
df_long = (
    df[['artist_id','common_name','wiki_url','genre_list']]
      .explode('genre_list')
      .rename(columns={'genre_list':'genre'})
)
df_long['genre'] = df_long['genre'].str.strip().str.lower()
df_long = df_long[df_long['genre'] != '']

# 9) Save exploded table
exploded_path = out_dir / "artist_genres_exploded.csv"
df_long.to_csv(exploded_path, index=False, quoting=csv.QUOTE_ALL)
print(f"Saved long-format exploded genres to {exploded_path}")
