#!/usr/bin/env python3
"""
Script de scraping des paroles de Benabar depuis paroles.net
Usage: uv run -m scripts.scrape_benabar
"""

import httpx
from bs4 import BeautifulSoup
import json
import time
import re
from pathlib import Path
from datetime import date
from typing import Optional
import unicodedata

BASE_URL = "https://www.paroles.net"
ARTIST_PAGES = [
    "/benabar",
]
OUTPUT_PATH = Path("data/artists/benabar.json")
DELAY_SECONDS = 2
HEADERS = {"User-Agent": "ParodleBot/1.0 (Educational lyrics game project)"}


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text


def get_song_list() -> list[dict[str, str]]:
    """Fetch list of all song URLs from artist pages."""
    songs = []
    seen_urls = set()

    for page_path in ARTIST_PAGES:
        url = f"{BASE_URL}{page_path}"
        print(f"Fetching song list from {url}...")

        try:
            response = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=30)
            response.raise_for_status()
        except httpx.HTTPError as e:
            print(f"Error fetching {url}: {e}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        # Find all song links
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "/benabar/paroles-" in href and href not in seen_urls:
                title = link.get_text(strip=True)
                if title:
                    seen_urls.add(href)
                    full_url = href if href.startswith("http") else f"{BASE_URL}{href}"
                    songs.append({"url": full_url, "title": title})

        time.sleep(DELAY_SECONDS)

    return songs


def extract_year_from_copyright(text: str) -> Optional[int]:
    """Extract year from copyright text."""
    match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
    if match:
        return int(match.group(1))
    return None


def scrape_song(url: str, title: str) -> Optional[dict]:
    """Scrape lyrics from a single song page."""
    try:
        response = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=30)
        response.raise_for_status()
    except httpx.HTTPError as e:
        print(f"  Error fetching {url}: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # Try to find lyrics in the song-text div
    lyrics_div = soup.find("div", class_="song-text")

    if not lyrics_div:
        # Try alternative: look for the main content area
        lyrics_div = soup.find("div", class_="song-content")

    if not lyrics_div:
        # Try to find any large text block that looks like lyrics
        for div in soup.find_all("div"):
            text = div.get_text()
            # Lyrics typically have multiple line breaks
            if text.count("\n") > 10 and len(text) > 200:
                lyrics_div = div
                break

    if not lyrics_div:
        print(f"  Could not find lyrics for: {title}")
        return None

    # Extract raw lyrics text
    lyrics_text = lyrics_div.get_text("\n", strip=False)

    # Clean up the text
    lines = lyrics_text.split("\n")
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line:
            cleaned_lines.append(line)

    if not cleaned_lines:
        print(f"  Empty lyrics for: {title}")
        return None

    # Split into verses (groups of consecutive non-empty lines)
    verses = []
    current_verse = []

    for line in cleaned_lines:
        if line:
            current_verse.append(line)
        elif current_verse:
            verses.append({"verse_number": len(verses) + 1, "lines": current_verse})
            current_verse = []

    if current_verse:
        verses.append({"verse_number": len(verses) + 1, "lines": current_verse})

    # If no verse separation found, treat all as one verse
    if not verses and cleaned_lines:
        verses = [{"verse_number": 1, "lines": cleaned_lines}]

    # Try to extract year from JSON-LD or page content
    year = None
    script_tags = soup.find_all("script", type="application/ld+json")
    for script in script_tags:
        try:
            data = json.loads(script.string)
            if "copyrightYear" in data:
                year = int(data["copyrightYear"])
                break
            if "datePublished" in data:
                year = extract_year_from_copyright(data["datePublished"])
                if year:
                    break
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    # Also look for year in page text
    if not year:
        copyright_text = soup.get_text()
        year = extract_year_from_copyright(copyright_text)

    # Generate slug from URL
    slug = url.split("/")[-1].replace("paroles-", "")

    return {"id": slug, "title": title, "album": None, "year": year, "lyrics": verses, "full_text": "\n".join(cleaned_lines)}


def main():
    print("=" * 50)
    print("Scraping des paroles de Benabar")
    print("=" * 50)

    # Get song list
    print("\nRecuperation de la liste des chansons...")
    songs = get_song_list()
    print(f"Trouve {len(songs)} chansons")

    if not songs:
        print("Aucune chanson trouvee. Verifiez la connexion et l'URL.")
        return

    # Scrape each song
    all_songs = []
    failed = []

    for i, song_info in enumerate(songs):
        print(f"\n[{i + 1}/{len(songs)}] {song_info['title']}")

        lyrics_data = scrape_song(song_info["url"], song_info["title"])

        if lyrics_data:
            all_songs.append(lyrics_data)
            print(f"  OK - {len(lyrics_data['lyrics'])} couplets")
        else:
            failed.append(song_info["title"])

        time.sleep(DELAY_SECONDS)

    # Save to JSON
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    output_data = {"songs": all_songs, "metadata": {"total_songs": len(all_songs), "scraped_date": str(date.today()), "source": "paroles.net", "artist": "Bénabar"}}

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    print(f"Termine!")
    print(f"  Reussi: {len(all_songs)} chansons")
    print(f"  Echoue: {len(failed)} chansons")
    print(f"  Sauvegarde: {OUTPUT_PATH}")

    if failed:
        print(f"\nChansons echouees:")
        for title in failed:
            print(f"  - {title}")


if __name__ == "__main__":
    main()

