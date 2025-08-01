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
# We dont know who exactly some of the memebers are (their name)
# ────────────────────────────────────────────────────────────────

# %% 3.B check for orphan orgiginal performance IDs in covers.csv & originals.csv
# -- 3.B check for orphan orgiginal performance IDs in covers.csv & originals.csv

cov_org_ids = set(df_cov['org_perf_id'].astype(int))
orig_perf_ids = set(df_orig['perf_id'].astype(int))
missing_cov_org = sorted(cov_org_ids - orig_perf_ids)
print(f"Found {len(missing_cov_org)} org_perf_id [covers.csv] not in perf_id [originals.csv]:\n", missing_cov_org[:20])

# org_perf_id in covers.csv should match perf_id in originals.csv

# Interpretation: 
# lucky us, 
# ────────────────────────────────────────────────────────────────

# %% 3.C check for orphan orgiginal artist IDs
# -- 3.C check for orphan orgiginal artist IDs

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
# Interpretation if we find any mismatch:
# ────────────────────────────────────────────────────────────────

# %% 3.D check for orphan release artist IDs in releases.csv
# -- 3.D check for orphan release artist IDs in releases.csv

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
# ────────────────────────────────────────────────────────────────

# %% 3.E check for orphan cover performance IDs in releases.csv
# -- 3.E check for orphan cover performance IDs in releases.csv

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
missing_cov_perf = sorted(cov_perf_ids - rel_perf_ids)
print(f"Found {len(missing_cov_perf)} perf_id [covers.csv] not in perf_ids [releases.csv]:\n", missing_cov_perf[:20])
# Interpretation if we find any mismatch:
# ────────────────────────────────────────────────────────────────

# %%
