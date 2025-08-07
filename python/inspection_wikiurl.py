# This file explores the presence of `wiki_url` in the artists dataset

# %% 0. Load libraries & set project root
# -- 0. Load libraries & set project root --
# Import necessary libraries

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
import ast

# %% 1. Load raw data
# -- 1. Load raw data --
artists_path = project_root / "data" / "raw" / "neo4j_artists.csv"
covers_path = project_root / "data" / "raw" / "covers.csv"
originals_path = project_root / "data" / "raw" / "originals.csv"
releases_path = project_root / "data" / "raw" / "releases.csv"

df_art = pd.read_csv(artists_path, dtype=str, keep_default_na=False)
df_cov = pd.read_csv(covers_path, dtype=str, keep_default_na=False)
df_org = pd.read_csv(originals_path, dtype=str, keep_default_na=False)
df_rel = pd.read_csv(releases_path, dtype=str, keep_default_na=False)

# Normalize wiki_url column
# Treat empty strings and explicit NaNs the same way
df_art['wiki_url'] = df_art['wiki_url'].replace('', pd.NA)

# %% 2. extract artists with no wiki_url
# -- 2. Extract artists with no wiki_url --

df_art_no_wiki = df_art[df_art["wiki_url"].isna()]


# %% Overall Ratio of artists with no wiki_url
# -- Overall Ratio of artists with no wiki_url --

total_artists   = len(df_art)
no_wiki_overall = df_art['wiki_url'].isna().sum()
with_wiki_overall = total_artists - no_wiki_overall
ratio_overall   = no_wiki_overall / total_artists
print(f"Total artists: {total_artists}")
print(f"Artists with no wiki_url: {no_wiki_overall} ({ratio_overall:.2%})")
print(f"Artists with wiki_url: {with_wiki_overall} ({1 - ratio_overall:.2%})")

# %% Artists in Originals with no wiki_url
# -- Artists in Originals with no wiki_url --
# Extract the IDs
org_ids = (
    df_org['org_art_id']
    .apply(ast.literal_eval)   # '[1, 3]' → [1, 3]
    .explode()                 # one row per ID
    .astype(int)
    .unique()
)

# Look them up in df_art
mask_org        = df_art['artist_id'].astype(int).isin(org_ids)
total_org       = mask_org.sum()
no_wiki_org     = df_art.loc[mask_org, 'wiki_url'].isna().sum()
ratio_org       = no_wiki_org / total_org

print(f"Artists in Originals: {total_org}")
print(f"Artists in Originals with no wiki_url: {no_wiki_org} ({ratio_org:.2%})")
print(f"Artists in Originals with wiki_url: {total_org - no_wiki_org} ({1 - ratio_org:.2%})")

# %% Artists in Covers with no wiki_url
# -- Artists in Covers with no wiki_url --
# Extract the IDs
cov_ids = (
    df_cov['cov_art_id']
    .apply(ast.literal_eval)
    .explode()
    .astype(int)
    .unique()
)

# Look them up in df_art
mask_cov      = df_art['artist_id'].astype(int).isin(cov_ids)
total_cov     = mask_cov.sum()
no_wiki_cov   = df_art.loc[mask_cov, 'wiki_url'].isna().sum()
ratio_cov     = no_wiki_cov / total_cov

print(f"Artists in Covers: {total_cov}")
print(f"Artists in Covers with no wiki_url: {no_wiki_cov} ({ratio_cov:.2%})")
print(f"Artists in Covers with wiki_url: {total_cov - no_wiki_cov} ({1 - ratio_cov:.2%})")

# %% Artists in Releases with no wiki_url
# -- Artists in Releases with no wiki_url --
# Extract the IDs
rel_ids = (
    df_rel['artist_id']
    .apply(ast.literal_eval)
    .explode()
    .astype(int)
    .unique()
)

# Look them up in df_art
mask_rel      = df_art['artist_id'].astype(int).isin(rel_ids)
total_rel     = mask_rel.sum()
no_wiki_rel   = df_art.loc[mask_rel, 'wiki_url'].isna().sum()
ratio_rel     = no_wiki_rel / total_rel

print(f"Artists in Releases: {total_rel}")
print(f"Artists in Releases with no wiki_url: {no_wiki_rel} ({ratio_rel:.2%})")
print(f"Artists in Releases with wiki_url: {total_rel - no_wiki_rel} ({1 - ratio_rel:.2%})")

# %% Entanglement: originals WITH wiki_url covered BY artists WITHOUT wiki_url (vectorized)
# -- Faster entanglement analysis --

# Flag artists that have a wiki entry
df_art['has_wiki'] = df_art['wiki_url'].notna()
from collections import defaultdict
has_wiki_map = defaultdict(lambda: False, df_art.set_index('artist_id')['has_wiki'].to_dict())

# --- Expand the covers table to one row per covering artist ---
cov_exp = (
    df_cov
    .assign(cov_art_id=df_cov['cov_art_id'].apply(ast.literal_eval))
    .explode('cov_art_id')
    .rename(columns={'cov_art_id': 'cover_artist_id'})
)
cov_exp['cover_artist_id'] = cov_exp['cover_artist_id'].astype(str)
cov_exp['cover_artist_has_wiki'] = cov_exp['cover_artist_id'].map(has_wiki_map).astype(bool)

# --- Expand the originals table to one row per original artist ---
org_exp = (
    df_org
    .assign(org_art_id=df_org['org_art_id'].apply(ast.literal_eval))
    .explode('org_art_id')
    .rename(columns={'org_art_id': 'original_artist_id'})
)
org_exp['original_artist_id'] = org_exp['original_artist_id'].astype(str)
org_exp['original_artist_has_wiki'] = org_exp['original_artist_id'].map(has_wiki_map).astype(bool)

# Does each original performance have *any* artist with wiki_url?
orig_perf_has_wiki = (
    org_exp.groupby('perf_id')['original_artist_has_wiki']
            .any()
            .rename('original_has_wiki_any')
)

# --- Join back to the exploded covers ---
cov_exp = cov_exp.merge(orig_perf_has_wiki, left_on='org_perf_id', right_index=True, how='left')

# Identify entangled rows: cover‑artist has *no* wiki but original perf has *some* wiki
entangled_rows = cov_exp[(~cov_exp['cover_artist_has_wiki']) & (cov_exp['original_has_wiki_any'])]

entangled_count = entangled_rows['org_perf_id'].nunique()
print("\n=== Entanglement Summary (vectorized) ===")
print(f"Covers where an artist WITHOUT wiki_url covered an artist WITH wiki_url: {entangled_count}")

# Calculate the overall ratio (as a percentage) relative to all covered originals
total_covered_originals = df_cov['org_perf_id'].nunique()
ratio_no_wiki_covers_wiki = entangled_count / total_covered_originals if total_covered_originals else 0
print(f"Overall ratio: {ratio_no_wiki_covers_wiki:.2%}")


# Show up to 10 distinct examples for quick inspection
if entangled_count:
    example_perfs = entangled_rows.groupby('org_perf_id').head(1).head(10)
    for _, row in example_perfs.iterrows():
        print(
            f"→ '{row['song_title']}' ({row['perf_year']}) | "
            f"Cover artist {row['cover_artist_id']} (no wiki) | "
            f"Original performance ID {row['org_perf_id']} (has wiki)"
        )

# %% Entanglement: originals WITHOUT wiki_url covered BY artists WITH wiki_url (vectorized)
# -- Reverse entanglement analysis --

# Identify entangled rows: cover‑artist HAS wiki but original perf has NO wiki at all
entangled_rows_rev = cov_exp[(cov_exp['cover_artist_has_wiki']) & (~cov_exp['original_has_wiki_any'])]

entangled_count_rev = entangled_rows_rev['org_perf_id'].nunique()
print("\n=== Reverse Entanglement Summary (vectorized) ===")
print(f"Covers where an artist WITH wiki_url covered an artist WITHOUT wiki_url: {entangled_count_rev}")

# Calculate the overall ratio (as a percentage) relative to all covered originals
total_covered_originals = df_cov['org_perf_id'].nunique()
ratio_wiki_covers_no_wiki = entangled_count_rev / total_covered_originals if total_covered_originals else 0
print(f"Overall ratio: {ratio_wiki_covers_no_wiki:.2%}")

# Show up to 10 distinct examples for quick inspection
if entangled_count_rev:
    example_perfs_rev = entangled_rows_rev.groupby('org_perf_id').head(1).head(10)
    for _, row in example_perfs_rev.iterrows():
        print(
            f"→ '{row['song_title']}' ({row['perf_year']}) | "
            f"Cover artist {row['cover_artist_id']} (with wiki) | "
            f"Original performance ID {row['org_perf_id']} (no wiki)"
        )

# %%
