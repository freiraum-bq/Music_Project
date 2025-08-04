def ordinal(n: int) -> str:
    """Return ordinal string for an integer, e.g., 3->'3rd', 21->'21st'."""
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"


#!/usr/bin/env python3
"""
Scrape award categories and winners from a given Wikipedia awards page.
"""
import requests
from bs4 import BeautifulSoup
import csv
import os


def get_project_root():
    # Project root is parent of this script's directory
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def scrape_awards(url: str):
    """Return a list of dicts with 'category', 'winner', and 'work'."""
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    # Locate the 'Award winners' section by its id anchor (could be on an <h2> or <span>)
    header_tag = soup.find(id='Award_winners')
    if header_tag:
        # The first <ul> after that heading contains the awards
        awards_list = header_tag.find_next('ul')
    else:
        # Fallback: search all <p> tags for the intro text
        intro = None
        for p in soup.find_all('p'):
            if 'The following awards were given' in p.get_text():
                intro = p
                break
        if not intro:
            raise RuntimeError("Could not find the awards section header or intro paragraph.")
        awards_list = intro.find_next_sibling('ul')
    if not awards_list:
        raise RuntimeError("Could not find the awards list <ul>.")

    awards = []
    # For each top-level category
    for li in awards_list.find_all('li', recursive=False):
        # Category name
        cat_link = li.find('a')
        category = cat_link.get_text(strip=True) if cat_link else li.get_text(strip=True)

        # Nested <ul> contains winner(s)
        nested = li.find('ul')
        if not nested:
            continue

        # Process each nominee and winner in this category
        for item in nested.find_all('li', recursive=False):
            # Determine if this item is the winner (bolded) or a nominee
            bold_tag = item.find('b')
            if bold_tag:
                role = 'winner'
                source = bold_tag
            else:
                role = 'nominee'
                source = item

            # Artist name: first <a> within the source
            artist_a = source.find('a')
            artist = artist_a.get_text(strip=True) if artist_a else source.get_text(strip=True)

            # Full text from the source, then remove artist name to isolate the work
            full_text = source.get_text(separator=' ', strip=True)
            rest = full_text.replace(artist, '').strip()
            # Remove leading 'for'
            work = rest
            if rest.lower().startswith('for '):
                work = rest[4:].strip(' "')

            awards.append({
                'category': category,
                'artist': artist,
                'work': work,
                'role': role
            })

    return awards


def main():
    root = get_project_root()
    out_dir = os.path.join(root, 'data', 'scraping', 'wiki_awards')
    os.makedirs(out_dir, exist_ok=True)

    all_awards = []
    for n in range(3, 64):
        ord_str = ordinal(n)
        url = f"https://en.wikipedia.org/wiki/{ord_str}_Annual_Grammy_Awards"
        print(f"Scraping {ord_str} ceremony at {url}")
        awards = scrape_awards(url)
        year = n + 1957
        for a in awards:
            a['ceremony'] = n
            a['year'] = year
        per_file = os.path.join(out_dir, f"{ord_str}_grammy_awards.csv")
        with open(per_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['ceremony', 'year', 'category', 'artist', 'work', 'role'])
            writer.writeheader()
            writer.writerows(awards)
        print(f"Saved {len(awards)} awards for ceremony {n} to {per_file}")
        all_awards.extend(awards)

    merged_file = os.path.join(out_dir, 'grammy_awards_3_to_63.csv')
    with open(merged_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['ceremony', 'year', 'category', 'artist', 'work', 'role'])
        writer.writeheader()
        writer.writerows(all_awards)
    print(f"Saved merged awards ({len(all_awards)} entries) to {merged_file}")


if __name__ == '__main__':
    main()