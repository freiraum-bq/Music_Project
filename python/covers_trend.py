#%% set root path for imports
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

import pandas as pd
# Load data
path_to_raw_data = project_root / "data" / "raw"
df_art = pd.read_csv(path_to_raw_data / "neo4j_artists.csv")
df_orig = pd.read_csv(path_to_raw_data /  "originals.csv")
df_cov = pd.read_csv(path_to_raw_data / "covers.csv")
df_rel = pd.read_csv(path_to_raw_data / "releases.csv")


# %%
import matplotlib.pyplot as plt

# Filter data for years 1960–2020
df_cov['perf_year'] = pd.to_numeric(df_cov['perf_year'], errors='coerce')
df_orig['release_year'] = pd.to_numeric(df_orig['release_year'], errors='coerce')
df_cov = df_cov[(df_cov['perf_year'] >= 1960) & (df_cov['perf_year'] <= 2020)]
df_orig = df_orig[(df_orig['release_year'] >= 1960) & (df_orig['release_year'] <= 2020)]

# Deduplicate by performance ID to count unique performances
df_cov = df_cov[['perf_year', 'perf_id']].drop_duplicates()
df_orig = df_orig[['release_year', 'perf_id']].drop_duplicates()

# Compute decade for grouping in the deduplicated DataFrames
df_cov['decade'] = (df_cov['perf_year'] // 10) * 10
df_orig['decade'] = (df_orig['release_year'] // 10) * 10

# Count covers and originals by decade
cover_counts = df_cov.groupby('decade').size().reset_index(name='cover_count')
orig_counts = df_orig.groupby('decade').size().reset_index(name='original_count')

# Merge counts and calculate cover-to-original ratio
df_trend = pd.merge(cover_counts, orig_counts, on='decade', how='outer').fillna(0)
df_trend['cover_to_original_ratio'] = df_trend['cover_count'] / df_trend['original_count']
df_trend = df_trend.sort_values('decade')

# Display the resulting table
print(df_trend)

# Plot the trend
plt.figure(figsize=(8, 5))
plt.plot(df_trend['decade'], df_trend['cover_to_original_ratio'], marker='o')
plt.title('Cover-to-Original Ratio by Decade (1960–2020)')
plt.xlabel('Decade')
plt.ylabel('Cover Count / Original Count')
plt.xticks(df_trend['decade'])
plt.grid(True)
plt.tight_layout()
plt.show()

# Calculate share of covers among all performances by decade
df_trend['total_performances'] = df_trend['cover_count'] + df_trend['original_count']
df_trend['cover_share_pct'] = (df_trend['cover_count'] / df_trend['total_performances']) * 100
print("\nCover share (%) by decade:")
print(df_trend[['decade', 'cover_share_pct']])

# Plot cover share percentage
plt.figure(figsize=(8, 5))
plt.plot(df_trend['decade'], df_trend['cover_share_pct'], marker='o')
plt.title('Percentage of Covers Among All Performances by Decade (1960–2020)')
plt.xlabel('Decade')
plt.ylabel('Cover Share (%)')
plt.xticks(df_trend['decade'])
plt.grid(True)
plt.tight_layout()
plt.show()

# %%
