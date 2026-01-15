"""
Service de gestion des paroles.
Charge et fournit acces aux paroles depuis le fichier JSON.
"""

import json
import random
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from src.utils.text_processing import extract_words


@dataclass
class Song:
    """Represente une chanson."""
    id: str
    title: str
    album: Optional[str]
    year: Optional[int]
    lyrics: list[dict]  # Liste de couplets
    full_text: str


@dataclass
class LyricsData:
    """Donnees completes des paroles."""
    songs: list[Song]
    metadata: dict


class LyricsService:
    """Service de gestion des paroles."""

    def __init__(self, data_path: str = "data/lyrics.json"):
        self.data_path = Path(data_path)
        self.data: Optional[LyricsData] = None
        self._load_data()

    def _load_data(self) -> None:
        """Charge les donnees depuis le fichier JSON."""
        if not self.data_path.exists():
            print(f"Attention: Fichier de paroles non trouve: {self.data_path}")
            self.data = LyricsData(songs=[], metadata={})
            return

        with open(self.data_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        songs = []
        for song_data in raw_data.get('songs', []):
            song = Song(
                id=song_data['id'],
                title=song_data['title'],
                album=song_data.get('album'),
                year=song_data.get('year'),
                lyrics=song_data.get('lyrics', []),
                full_text=song_data.get('full_text', '')
            )
            # Filtre les chansons sans paroles
            if song.full_text and len(song.full_text) > 50:
                songs.append(song)

        self.data = LyricsData(
            songs=songs,
            metadata=raw_data.get('metadata', {})
        )

        print(f"Charge {len(self.data.songs)} chansons depuis {self.data_path}")

    def get_random_song(self) -> Optional[Song]:
        """Retourne une chanson aleatoire."""
        if not self.data or not self.data.songs:
            return None
        return random.choice(self.data.songs)

    def get_song_by_id(self, song_id: str) -> Optional[Song]:
        """Retourne une chanson par son ID."""
        if not self.data:
            return None
        for song in self.data.songs:
            if song.id == song_id:
                return song
        return None

    def get_all_songs(self) -> list[Song]:
        """Retourne toutes les chansons."""
        if not self.data:
            return []
        return self.data.songs

    def get_random_phrase(self, min_words: int = 5, max_words: int = 12) -> Optional[tuple[Song, str, list[str]]]:
        """
        Retourne une phrase aleatoire d'une chanson, alignee sur les retours a la ligne.

        Les phrases commencent et finissent aux limites de lignes pour etre coherentes.

        Returns:
            Tuple (chanson, texte_complet_phrase, liste_mots) ou None
        """
        song = self.get_random_song()
        if not song:
            return None

        # Split into lines and filter empty ones
        lines = [line.strip() for line in song.full_text.split('\n') if line.strip()]
        if not lines:
            return None

        # Convert lines to word lists
        line_words = [extract_words(line) for line in lines]
        line_words = [words for words in line_words if words]  # Filter empty

        if not line_words:
            return None

        # Try to find a valid phrase (multiple attempts)
        for _ in range(20):
            # Pick a random starting line
            start_line = random.randint(0, len(line_words) - 1)

            # Accumulate words from consecutive lines until we have enough
            phrase_words = []
            end_line = start_line

            while end_line < len(line_words) and len(phrase_words) < max_words:
                phrase_words.extend(line_words[end_line])
                end_line += 1

                # Stop if we have enough words
                if len(phrase_words) >= min_words:
                    break

            # Check if we got enough words
            if len(phrase_words) >= min_words:
                # Trim to max_words if needed (always end at line boundary)
                if len(phrase_words) > max_words:
                    # Find how many complete lines we can include
                    phrase_words = []
                    for i in range(start_line, end_line):
                        if len(phrase_words) + len(line_words[i]) <= max_words:
                            phrase_words.extend(line_words[i])
                        else:
                            break

                if len(phrase_words) >= min_words:
                    phrase_text = ' '.join(phrase_words)
                    return song, phrase_text, phrase_words

        return None

    def get_random_verse(self, song: Optional[Song] = None) -> Optional[tuple[Song, list[str]]]:
        """
        Retourne un couplet aleatoire.

        Args:
            song: Chanson specifique ou None pour aleatoire

        Returns:
            Tuple (chanson, lignes_du_couplet) ou None
        """
        if song is None:
            song = self.get_random_song()
        if not song or not song.lyrics:
            return None

        verse = random.choice(song.lyrics)
        return song, verse.get('lines', [])

    def count_songs(self) -> int:
        """Retourne le nombre de chansons disponibles."""
        if not self.data:
            return 0
        return len(self.data.songs)


# Instance globale du service
_lyrics_service: Optional[LyricsService] = None


def get_lyrics_service() -> LyricsService:
    """Retourne l'instance globale du service de paroles."""
    global _lyrics_service
    if _lyrics_service is None:
        _lyrics_service = LyricsService()
    return _lyrics_service
