"""
Schemas Pydantic pour l'API de jeu.
"""

from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class GameMode(str, Enum):
    """Modes de jeu disponibles."""
    WORD_GUESSING = "word_guessing"
    SONG_NAME = "song_name"


class WordGuessType(str, Enum):
    """Types de devinette de mot."""
    NEXT = "next"
    PREVIOUS = "previous"
    MISSING = "missing"


class ArtistSchema(BaseModel):
    """Schema pour un artiste."""
    id: str
    name: str
    song_count: int


class ArtistsResponse(BaseModel):
    """Reponse pour la liste des artistes."""
    artists: List[ArtistSchema]


class StartGameRequest(BaseModel):
    """Requete pour demarrer une partie."""
    mode: GameMode
    artist_id: str = "jacques-brel"  # Identifiant de l'artiste
    min_visible_words: int = 5  # Nombre minimum de mots visibles (sans compter ___)


class StartGameResponse(BaseModel):
    """Reponse au demarrage d'une partie."""
    session_id: str
    mode: GameMode
    phrase: str
    word_type: Optional[WordGuessType] = None
    max_guesses: int = 5
    current_round: int = 1
    total_rounds: int = 1


class GuessRequest(BaseModel):
    """Requete pour soumettre une reponse."""
    session_id: str
    guess: str


class PassRequest(BaseModel):
    """Requete pour passer une manche."""
    session_id: str


class RevealRequest(BaseModel):
    """Requete pour reveler le nom de la chanson."""
    session_id: str


class HintRequest(BaseModel):
    """Requete pour obtenir un indice."""
    session_id: str


class RoundResultSchema(BaseModel):
    """Resultat d'une manche pour le recap."""
    round: int
    answer: str
    song_title: str
    context: str
    points: int
    success: bool


class GuessResponse(BaseModel):
    """Reponse a une tentative."""
    correct: bool
    game_over: bool
    guesses_remaining: int
    points_earned: Optional[int] = None
    correct_answer: Optional[str] = None
    song_title: Optional[str] = None
    hint: Optional[str] = None
    phrase: Optional[str] = None
    time_seconds: Optional[float] = None
    error: Optional[str] = None
    # Multi-round fields
    round_complete: Optional[bool] = None
    round_failed: Optional[bool] = None
    current_round: Optional[int] = None
    total_rounds: Optional[int] = None
    round_score: Optional[int] = None
    cumulative_score: Optional[int] = None
    new_phrase: Optional[str] = None
    new_word_type: Optional[str] = None
    answer_context: Optional[str] = None
    round_results: Optional[List[RoundResultSchema]] = None


class SessionState(BaseModel):
    """Etat d'une session de jeu."""
    session_id: str
    mode: GameMode
    phrase: str
    word_type: Optional[WordGuessType] = None
    guesses_remaining: int
    game_over: bool


class StatsResponse(BaseModel):
    """Statistiques du jeu."""
    total_songs: int
    active_sessions: int
