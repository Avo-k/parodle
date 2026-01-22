#!/usr/bin/env python3
"""
Fetch song popularity from Spotify API and update artist JSON files.

Usage:
    python scripts/fetch_spotify_popularity.py

Environment variables (or edit CREDENTIALS below):
    SPOTIFY_CLIENT_ID: Spotify app client ID
    SPOTIFY_CLIENT_SECRET: Spotify app client secret
"""

import json
import os
import sys
from pathlib import Path

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
except ImportError:
    print("Error: spotipy not installed. Run: pip install spotipy")
    sys.exit(1)

try:
    from rapidfuzz import fuzz
except ImportError:
    print("Error: rapidfuzz not installed. Run: pip install rapidfuzz")
    sys.exit(1)

# Default credentials (can be overridden by environment variables)
CREDENTIALS = {
    "client_id": os.environ.get("SPOTIFY_CLIENT_ID", "bc56a243e59c44c9b0d5c894f3a6fee4"),
    "client_secret": os.environ.get("SPOTIFY_CLIENT_SECRET", "8fa743dd512c4d7587387d8c9cab995c"),
}

# Artist name mappings for Spotify search
ARTIST_SPOTIFY_NAMES = {
    "jacques-brel": "Jacques Brel",
    "benabar": "Bénabar",
}

# Minimum fuzzy match score to consider a match
MIN_MATCH_SCORE = 70

def get_spotify_client() -> spotipy.Spotify:
    """Create authenticated Spotify client."""
    auth_manager = SpotifyClientCredentials(
        client_id=CREDENTIALS["client_id"],
        client_secret=CREDENTIALS["client_secret"],
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def normalize_title(title: str) -> str:
    """Normalize song title for matching."""
    # Remove common suffixes and clean up
    title = title.lower().strip()
    # Remove parenthetical content like "(Live)" or "(Remastered)"
    import re
    title = re.sub(r'\s*\([^)]*\)\s*', ' ', title)
    title = re.sub(r'\s*\[[^\]]*\]\s*', ' ', title)
    # Remove extra whitespace
    title = ' '.join(title.split())
    return title


def fetch_artist_tracks(sp: spotipy.Spotify, artist_name: str) -> dict[str, int]:
    """Fetch all tracks for an artist with their popularity scores."""
    print(f"Searching for artist: {artist_name}")

    # Search for artist
    results = sp.search(q=f'artist:"{artist_name}"', type='artist', limit=1)
    if not results['artists']['items']:
        print(f"  Artist not found: {artist_name}")
        return {}

    artist = results['artists']['items'][0]
    artist_id = artist['id']
    print(f"  Found: {artist['name']} (ID: {artist_id})")

    track_popularity: dict[str, int] = {}

    # Get top tracks (most popular)
    print("  Fetching top tracks...")
    top_tracks = sp.artist_top_tracks(artist_id, country='FR')
    for track in top_tracks['tracks']:
        title = normalize_title(track['name'])
        if title not in track_popularity or track['popularity'] > track_popularity[title]:
            track_popularity[title] = track['popularity']

    # Get albums and their tracks
    print("  Fetching albums...")
    albums = []
    album_results = sp.artist_albums(artist_id, album_type='album,single', limit=50)
    albums.extend(album_results['items'])

    while album_results['next']:
        album_results = sp.next(album_results)
        albums.extend(album_results['items'])

    print(f"  Found {len(albums)} albums/singles")

    # Get tracks from each album
    for album in albums:
        try:
            album_tracks = sp.album_tracks(album['id'])
            for track in album_tracks['items']:
                # Need to get full track info for popularity
                try:
                    full_track = sp.track(track['id'])
                    title = normalize_title(full_track['name'])
                    if title not in track_popularity or full_track['popularity'] > track_popularity[title]:
                        track_popularity[title] = full_track['popularity']
                except Exception:
                    continue
        except Exception:
            continue

    print(f"  Total unique tracks found: {len(track_popularity)}")
    return track_popularity


def match_local_songs(
    local_songs: list[dict],
    spotify_tracks: dict[str, int],
    artist_name: str,
    sp: spotipy.Spotify,
) -> list[tuple[dict, int]]:
    """Match local songs with Spotify tracks and get popularity."""
    matched: list[tuple[dict, int]] = []

    for song in local_songs:
        local_title = normalize_title(song['title'])
        best_match = None
        best_score = 0
        best_popularity = 0

        # Try fuzzy matching with cached tracks
        for spotify_title, popularity in spotify_tracks.items():
            score = fuzz.ratio(local_title, spotify_title)
            if score > best_score and score >= MIN_MATCH_SCORE:
                best_score = score
                best_match = spotify_title
                best_popularity = popularity

        # If no good match, try direct Spotify search
        if best_score < MIN_MATCH_SCORE:
            try:
                query = f'track:"{song["title"]}" artist:"{artist_name}"'
                results = sp.search(q=query, type='track', limit=1)
                if results['tracks']['items']:
                    track = results['tracks']['items'][0]
                    best_popularity = track['popularity']
                    best_match = track['name']
                    best_score = 100  # Direct search match
            except Exception:
                pass

        if best_match:
            print(f"  ✓ {song['title']} -> {best_match} (score: {best_score}, popularity: {best_popularity})")
            matched.append((song, best_popularity))
        else:
            print(f"  ✗ {song['title']} -> No match found (assigning popularity 0)")
            matched.append((song, 0))

    return matched


def update_artist_file(artist_id: str, data_dir: Path) -> None:
    """Update a single artist's JSON file with popularity rankings."""
    json_path = data_dir / "artists" / f"{artist_id}.json"

    if not json_path.exists():
        print(f"File not found: {json_path}")
        return

    print(f"\n{'='*60}")
    print(f"Processing: {artist_id}")
    print(f"{'='*60}")

    # Load JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    songs = data.get('songs', [])
    if not songs:
        print("No songs found in file")
        return

    print(f"Local songs: {len(songs)}")

    # Get Spotify client
    sp = get_spotify_client()

    # Get artist name for Spotify
    artist_name = ARTIST_SPOTIFY_NAMES.get(artist_id, artist_id.replace('-', ' ').title())

    # Fetch Spotify tracks
    spotify_tracks = fetch_artist_tracks(sp, artist_name)

    # Match local songs with Spotify
    print("\nMatching songs...")
    matched = match_local_songs(songs, spotify_tracks, artist_name, sp)

    # Sort by popularity (descending) to assign ranks
    matched.sort(key=lambda x: x[1], reverse=True)

    # Assign popularity ranks (1 = most popular)
    song_ranks: dict[str, int] = {}
    for rank, (song, popularity) in enumerate(matched, start=1):
        song_ranks[song['id']] = rank

    # Update songs with ranks
    for song in songs:
        song['popularity_rank'] = song_ranks.get(song['id'], len(songs))

    # Save updated JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Updated {json_path}")
    print("\nTop 10 songs by popularity:")
    sorted_songs = sorted(songs, key=lambda x: x.get('popularity_rank', 999))
    for song in sorted_songs[:10]:
        print(f"  {song['popularity_rank']:2d}. {song['title']}")


def main():
    """Main entry point."""
    # Find data directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_dir = project_root / "data"

    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        sys.exit(1)

    # Find all artist files
    artists_dir = data_dir / "artists"
    if not artists_dir.exists():
        print(f"Artists directory not found: {artists_dir}")
        sys.exit(1)

    artist_files = list(artists_dir.glob("*.json"))
    print(f"Found {len(artist_files)} artist file(s)")

    for artist_file in artist_files:
        artist_id = artist_file.stem
        update_artist_file(artist_id, data_dir)

    print("\n" + "="*60)
    print("Done! All artist files updated with popularity rankings.")
    print("="*60)


if __name__ == "__main__":
    main()
