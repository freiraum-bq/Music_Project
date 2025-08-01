# %% 1. Set root for Music_Project
# -- 1. Set root for Music_Project
import sys
import os
from pathlib import Path

# 1) Locate this script (or notebook) directory
try:
    script_dir = Path(__file__).resolve().parent
except NameError:
    # __file__ doesn't exist in notebooks or REPLs
    script_dir = Path.cwd()

# 2) Assume project root is one level up from `python/`
project_root = script_dir.parent

# 3) Sanity check: ensure there's a `data/` folder at the root
if not (project_root / "data").is_dir():
    raise RuntimeError(f"Project root {project_root!r} has no data/ folder.")

# 4) Prepend to sys.path so you can `import` anywhere in Music_Project
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
# ────────────────────────────────────────────────────────────────

# %% 2. load data & libraries
# -- 2. load data & libraries
import pandas as pd

path_to_raw_data = project_root / "data" / "raw"

df_art = pd.read_csv(path_to_raw_data / "neo4j_artists.csv")
df_orig = pd.read_csv(path_to_raw_data /  "originals.csv")
df_cov = pd.read_csv(path_to_raw_data / "covers.csv")
df_rel = pd.read_csv(path_to_raw_data / "releases.csv")
# ────────────────────────────────────────────────────────────────

# %% 3.A check for orphan member_of IDs in neo4j_artists.csv
# -- 3.A check for orphan member_of IDs in neo4j_artists.csv
member_series = (
    df_art['member_of']
      .dropna()
      .astype(str)
      .str.strip('[]')          # remove leading/trailing brackets
      .str.split(',')           # split on commas now
      .explode()                
      .str.strip()              # trim whitespace
      .loc[lambda s: s != '']   # drop any empty strings
)

# turn them into ints (if you like)
member_ids = set(member_series.astype(int))

# your existing artist IDs
artist_ids = set(df_art['artist_id'].astype(int))

# find truly missing IDs
missing_ids = sorted(member_ids - artist_ids)

print(f"Found {len(missing_ids)} member_of IDs not in artist_id:\n", missing_ids[:20])

# member_of IDs in neo4j_artists.csv should match artist_id in neo4j_artists.csv

# Interpretation:
# These IDs appear in member_of but there’s no matching artist row—
# It means our artists table is missing entries for those groups.

# %% 3.A.1 check for references to missing member_of IDs
# -- 3.A.1 check for references to missing member_of IDs
# --------------- member_of ➜ artist_id ----------------

for missing in missing_ids:
    refs = df_art[df_art['member_of'].str.contains(fr'\b{missing}\b', na=False)]
    print(f"→ ID {missing} is referenced by:",
          refs[['artist_id','common_name','member_of']].to_dict('records'))
# ────────────────────────────────────────────────────────────────

# %% 3.B check for orphan orgiginal performance IDs in covers.csv & originals.csv
# -- 3.B check for orphan orgiginal performance IDs in covers.csv & originals.csv
# ----------------- covers.org_perf_id ➜ originals.perf_id ----------------------

cov_org_ids = set(df_cov['org_perf_id'].astype(int))
orig_perf_ids = set(df_orig['perf_id'].astype(int))
missing_cov_org = sorted(cov_org_ids - orig_perf_ids)
print(f"Found {len(missing_cov_org)} org_perf_id [covers.csv] not in perf_id [originals.csv]:\n", missing_cov_org[:20])

# org_perf_id in covers.csv should match perf_id in originals.csv

# Interpretation: 
# lucky us !
# every cover in covers.csv points back to an existing original performance in originals.csv.
# ────────────────────────────────────────────────────────────────

# %% 3.C check for orphan orgiginal artist IDs
# -- 3.C check for orphan orgiginal artist IDs
# ----- originals.org_art_id ➜ artist_id -----

orig_art_series = (
    df_orig['org_art_id']
      .dropna()
      .astype(str)
      .str.strip('[]')
      .str.split(',')
      .explode()
      .str.strip()
      .loc[lambda s: s != '']
)
orig_art_ids = set(orig_art_series.astype(int))
artist_ids = set(df_art['artist_id'].astype(int))
missing_orig_art = sorted(orig_art_ids - artist_ids)
print(f"Found {len(missing_orig_art)} org_art_id [originals.csv] not in artist_id [neo4j_artists.csv]:\n", missing_orig_art[:20])

# org_art_id in originals.csv should match artist_id in neo4j_artists.csv
# Interpretation:
# 238 distinct original-artist IDs for which we have no corresponding artist record;
# for those 238 IDs we have a song release but no metadata
# ────────────────────────────────────────────────────────────────

# %% 3.C.1 Inspect missing original-artist IDs
# -- 3.C.1 Inspect missing original-artist IDs

# Explode originals so each org_art_id maps to its name
exploded_orig = (
    df_orig[['org_art_id','org_art_name']]
      .dropna(subset=['org_art_id'])
      .assign(org_art_id_clean=lambda d: d['org_art_id'].astype(str)
                                             .str.strip('[]')
                                             .str.split(','))
      .explode('org_art_id_clean')
      .assign(org_art_id_clean=lambda d: d['org_art_id_clean'].str.strip())
      .assign(org_art_id_int=lambda d: d['org_art_id_clean'].astype(int))
)

# Filter to missing IDs and display unique pairs
missing_orig_df = (    exploded_orig[exploded_orig['org_art_id_int'].isin(missing_orig_art)]
      [['org_art_id_int','org_art_name']]
        .drop_duplicates()
        .rename(columns={'org_art_id_int':'org_art_id'})
        .sort_values('org_art_id')
)
print(missing_orig_df.to_string(index=False))
# ────────────────────────────────────────────────────────────────

# %% 3.D check for orphan release artist IDs in releases.csv
# -- 3.D check for orphan release artist IDs in releases.csv
# ------------ releases.artist_id ➜ artist_id --------------

rel_art_series = (
    df_rel['artist_id']
      .dropna()
      .astype(str)
      .str.strip('[]')
      .str.split(',')
      .explode()
      .str.strip()
      .loc[lambda s: s != '']
)
rel_art_ids = set(rel_art_series.astype(int))
missing_rel_art = sorted(rel_art_ids - artist_ids)
print(f"Found {len(missing_rel_art)} artist_id [releases.csv] not in artist_id [neo4j_artists.csv]:\n", missing_rel_art[:20])

# releases.artist_id should match artists.artist_id
# Interpretation if we find any mismatch:
# we have release entries that reference artists not in our master artist list.
# ────────────────────────────────────────────────────────────────

# %% 3.D.1 Inspect missing release-artist IDs
# -- 3.D.1 Inspect missing release-artist IDs

# Explode `artist_id` lists so each row has one artist_id_int
exploded_rel = (
    df_rel[['release_id','artist_id','artist_name','release_title']]
      .dropna(subset=['artist_id'])
      .assign(artist_id_clean=lambda d: d['artist_id'].astype(str)
                                             .str.strip('[]')
                                             .str.split(','))
      .explode('artist_id_clean')
      .assign(artist_id_clean=lambda d: d['artist_id_clean'].str.strip())
      .assign(artist_id_int=lambda d: d['artist_id_clean'].astype(int))
)

# Filter to only those missing in master artist list
missing_rel_df = (
    exploded_rel[exploded_rel['artist_id_int'].isin(missing_rel_art)]
      [['artist_id_int','artist_name','release_id','release_title']]
      .drop_duplicates()
      .sort_values('artist_id_int')
)

print(missing_rel_df.to_string(index=False))
# ────────────────────────────────────────────────────────────────

# %% 3.E check for orphan cover performance IDs in releases.csv
# -- 3.E check for orphan cover performance IDs in releases.csv
# ------------- covers.perf_id ➜ releases.perf_ids ------------

perf_ids_series = (
    df_rel['perf_ids']
       .dropna()
       .astype(str)
       .str.strip('[]')
       .str.split(',')
       .explode()
       .str.strip()
       .loc[lambda s: s != '']
)
rel_perf_ids = set(perf_ids_series.astype(int))
cov_perf_ids = set(df_cov['perf_id'].astype(int))
# -- Show missing cover perf_ids in releases
missing_cov_perf = sorted(cov_perf_ids - rel_perf_ids)
print(f"Found {len(missing_cov_perf)} perf_id [covers.csv] not in perf_ids [releases.csv]:\n", missing_cov_perf[:20])
# Also show how many cover perf_ids DO match releases.perf_ids
matching_cov_perf = sorted(cov_perf_ids & rel_perf_ids)
print(
    f"Found {len(matching_cov_perf)} perf_id [covers.csv] that DO appear in perf_ids [releases.csv]:\n",
    matching_cov_perf[:20]
)
# Interpretation:
# Most of the covers are also "released" in releases.csv,
# but some covers seem just to be released as covers without a release entry.
# ────────────────────────────────────────────────────────────────

# %%
