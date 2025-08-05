

#!/usr/bin/env python3
"""
Script to count how many language translations exist for each artist's Wikipedia page.
Reads `data/neo4j_artists.csv`, retrieves each `wiki_url`, and uses the MediaWiki API
to count the number of interlanguage links (translations) for that page.
Outputs results to `data/artist_lang_counts.csv`.
"""
import os
import sys
import pandas as pd
import requests


def get_project_root():
    """Traverse up from this script until a folder with 'data' exists."""
    cwd = os.path.dirname(os.path.abspath(__file__))
    while not os.path.isdir(os.path.join(cwd, 'data')):
        parent = os.path.dirname(cwd)
        if parent == cwd:
            raise RuntimeError("Could not find 'Data' directory in any parent")
        cwd = parent
    return cwd


def count_langlinks(page_title: str) -> int:
    """Use the MediaWiki API to query all language links for a given page title."""
    session = requests.Session()
    api_url = 'https://en.wikipedia.org/w/api.php'
    params = {
        'action': 'query',
        'titles': page_title,
        'prop': 'langlinks',
        'lllimit': 'max',
        'format': 'json'
    }
    total = 0
    while True:
        resp = session.get(api_url, params=params)
        resp.raise_for_status()
        data = resp.json()
        pages = data.get('query', {}).get('pages', {})
        for page in pages.values():
            links = page.get('langlinks', [])
            total += len(links)
        if 'continue' in data:
            # follow continuation
            params.update(data['continue'])
        else:
            break
    return total


def main():
    root = get_project_root()
    csv_in = os.path.join(root, 'data', 'raw', 'neo4j_artists.csv')
    df = pd.read_csv(csv_in)

    results = []
    for _, row in df.iterrows():
        wiki_url = row.get('wiki_url', '')
        name = row.get('common_name', 'Unknown')

        # Skip if no valid wiki_url
        if not isinstance(wiki_url, str) or '/wiki/' not in wiki_url:
            print(f"Skipping {name}: no valid wiki_url")
            continue

        # Extract page title
        page_title = wiki_url.rsplit('/wiki/', 1)[-1]

        # Fail-safe: skip on fetch/parsing errors
        try:
            lang_count = count_langlinks(page_title)
        except Exception as e:
            print(f"Skipping {name} ({page_title}): error fetching URL: {e}")
            continue

        # Append successful result
        results.append({
            'artist_id': row.get('artist_id'),
            'common_name': name,
            'wiki_url': wiki_url,
            'language_count': lang_count
        })
        print(f"{name}: {lang_count}")

    out_df = pd.DataFrame(results)
    csv_out = os.path.join(root, 'data', 'scraping', 'artist_lang_counts.csv')
    out_df.to_csv(csv_out, index=False)
    print(f"Saved language counts to {csv_out}")


if __name__ == '__main__':
    main()