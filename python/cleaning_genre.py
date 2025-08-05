#!/usr/bin/env python3
"""
cleaning_genre.py

Processes the scraped artist_genres_raw.csv to produce 
wide-format genre tables.
"""
# %% 1. Import necessary libraries
# -- 1. Import necessary libraries --
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
import requests
from bs4 import BeautifulSoup

# %% 2 Load scraped genres
# -- 2 Load scraped genres --
raw_path = project_root / "data" / "scraping" / "genre" / "artist_genres_raw.csv"
df = pd.read_csv(raw_path, dtype=str, keep_default_na=False)

# %% 3. Clean and process genres
# -- 3. Clean and process genres --
# Clean numeric artifacts like [|1|], [|2|], etc.
df['genres_clean'] = df['genres'].str.replace(r'\[\|\d+\|\]', '', regex=True)


# Split on pipe into lists
df['genre_list'] = df['genres_clean'].str.split('|')

# Clean individual genre labels by removing parentheses and stray symbols
def clean_label(label: str) -> str:
    # Remove parenthetical content
    label = re.sub(r'\([^)]*\)', '', label)
    # Keep only letters, digits, spaces, hyphens, and ampersands
    label = re.sub(r'[^A-Za-z0-9\s\-\&]', '', label)
    # Collapse extra spaces and normalize case
    label = re.sub(r'\s+', ' ', label).strip()
    return label.lower()

# Apply cleaning to each entry in genre_list
df['genre_list'] = df['genre_list'].apply(
    lambda lst: [clean_label(g) for g in lst if clean_label(g)]
)

# Determine max genres per artist
max_genres = int(df['genre_list'].apply(lambda lst: len(lst) if isinstance(lst, list) else 0).max())

# Create wide-format columns genre_1 ... genre_N
for idx in range(max_genres):
    col = f'genre_{idx+1}'
    df[col] = df['genre_list'].apply(
        lambda lst: lst[idx].strip().lower() if isinstance(lst, list) and idx < len(lst) else ''
    )
df.drop(columns=['genres', 'genres_clean', 'genre_list'], inplace=True)

# %% 4. Save cleaned long-format genres
# -- 4. Save cleaned long-format genres --

dir = project_root / "data" / "scraping" / "genre"
dir.mkdir(parents=True, exist_ok=True)
path = dir / "artist_genres_clean.csv"
df.to_csv(path, index=False, quoting=csv.QUOTE_ALL)
print(f"Saved wide-format genres to {path}")

# %% 5. Cluster genres into main genres
# -- 5. Cluster genres into main genres --

df_mapping = pd.read_csv(dir / "genre_mapping.csv", dtype=str)
df_artists = pd.read_csv(dir / "artist_genres_clean.csv", dtype=str)

# Map subgenres to main genres and error on unmapped
# Build lookup dict: normalized lowercase subgenre -> lowercase main_genre
mapping_dict = {
    row['subgenre'].strip().lower(): row['main_genre'].strip().lower()
    for _, row in df_mapping.iterrows()
    if isinstance(row.get('subgenre'), str) and isinstance(row.get('main_genre'), str)
}

# Identify all genre_x columns
genre_cols = [col for col in df_artists.columns if col.startswith('genre_')]

# Create new main_genre_x columns based on mapping_dict
for col in genre_cols:
    main_col = f"main_{col}"
    df_artists[main_col] = (
        df_artists[col]
          .str.strip()
          .str.lower()
          .map(mapping_dict)
          .fillna('')  # leave empty if no mapping found
    )

# 6) Save clustered genres to CSV
clustered_path = dir / "artist_genres_clustered.csv"
df_artists.to_csv(clustered_path, index=False, quoting=csv.QUOTE_ALL)
print(f"Saved clustered genres to {clustered_path}")

# %% 6. Which subgenres are not mapped?
# -- 6. Which subgenres are not mapped? --

# Build set of all unmapped subgenres
unmapped = set()
for col in genre_cols:
    for val in df_artists[col].dropna().unique():
        v = val.strip().lower()
        if v and v not in mapping_dict:
            unmapped.add(v)

# Report unmapped subgenres
if unmapped:
    print(f"Found {len(unmapped)} unmapped subgenres:")
    for sub in sorted(unmapped):
        print("  -", sub)
else:
    print("All subgenres were successfully mapped.")

# %% 7. Identify artists with no main_genre entries
# -- 7. Identify artists with no main_genre entries --
# Identify artists with no main_genre entries
# Identify all main_genre_x columns
main_cols = [col for col in df_artists.columns if col.startswith('main_genre_')]

mask_no_main = df_artists[main_cols].eq('').all(axis=1)
missing_main = df_artists.loc[mask_no_main, ['artist_id', 'common_name']]
if not missing_main.empty:
    print("\nArtists with no main_genre assigned:")
    print(missing_main.to_string(index=False))
else:
    print("\nAll artists have at least one main_genre assigned.")


# %% X. Sanity check - how many main genres are there atm
# -- X. Sanity check - how many main genres are there atm --


# Collect distinct main genres
distinct_main = set()
for col in main_cols:
    distinct_main.update(df_artists[col].dropna().unique())

# Print the count and sorted list of distinct main genres
print(f"Found {len(distinct_main)} distinct main genres across main genre columns:")
print(sorted(distinct_main))


# %%
