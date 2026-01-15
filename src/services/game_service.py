"""
Service de logique de jeu.
Gere les sessions et la logique des differents modes.
"""

import uuid
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from src.services.lyrics_service import get_lyrics_service, Song
from src.services.scoring_service import calculate_score
from src.utils.text_processing import (
    words_match,
    extract_words,
    create_phrase_with_blank,
    split_into_chunks
)


class GameMode(str, Enum):
    """Modes de jeu disponibles."""
    WORD_GUESSING = "word_guessing"
    SONG_NAME = "song_name"


class WordGuessType(str, Enum):
    """Types de devinette de mot."""
    NEXT = "next"
    PREVIOUS = "previous"
    MISSING = "missing"


@dataclass
class RoundResult:
    """Resultat d'une manche."""
    round_number: int
    answer: str
    song_title: str
    context: str
    points: int
    success: bool  # True = trouve, False = passe ou echoue


@dataclass
class GameSession:
    """Session de jeu."""
    session_id: str
    mode: GameMode
    song: Song
    answer: str
    phrase: str
    word_type: Optional[WordGuessType] = None
    guesses_remaining: int = 5
    guesses_made: list[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    hints_revealed: int = 0
    all_hints: list[str] = field(default_factory=list)
    game_over: bool = False
    correct: bool = False
    # Multi-round support (for word guessing)
    current_round: int = 1
    total_rounds: int = 1
    cumulative_score: int = 0
    round_start_time: float = field(default_factory=time.time)
    min_visible_words: int = 5  # Nombre minimum de mots visibles
    round_results: list[RoundResult] = field(default_factory=list)  # Historique des manches


# Stockage des sessions en memoire
_sessions: dict[str, GameSession] = {}


def _generate_session_id() -> str:
    """Genere un ID de session unique."""
    return str(uuid.uuid4())[:8]


def _get_answer_context(song: Song, answer: str, context_words: int = 20) -> str:
    """
    Extrait le contexte autour de la reponse dans la chanson (avec retours a la ligne).

    Args:
        song: La chanson
        answer: Le mot reponse
        context_words: Nombre total de mots de contexte (avant + apres)

    Returns:
        Contexte avec retours a la ligne preserves
    """
    from src.utils.text_processing import normalize_french

    # Trouve la position du mot dans le texte complet (avec \n preserves)
    full_text = song.full_text
    normalized_answer = normalize_french(answer)

    # Trouve toutes les occurrences du mot dans le texte
    lines = full_text.split('\n')
    all_words = []
    word_to_line = {}  # Map word_index -> (line_num, position_in_line)

    word_idx = 0
    for line_num, line in enumerate(lines):
        line_words = line.split()
        for pos_in_line, word in enumerate(line_words):
            all_words.append(word)
            word_to_line[word_idx] = (line_num, pos_in_line, line_words)
            word_idx += 1

    # Trouve l'index du mot reponse
    answer_idx = -1
    for i, word in enumerate(all_words):
        if normalize_french(word) == normalized_answer:
            answer_idx = i
            break

    if answer_idx == -1:
        # Fallback: retourne juste les premieres lignes
        return '\n'.join(lines[:5])

    # Extrait context_words mots autour
    words_before = context_words // 2
    words_after = context_words - words_before

    start_idx = max(0, answer_idx - words_before)
    end_idx = min(len(all_words), answer_idx + words_after + 1)

    # Determine les lignes couvertes
    if start_idx not in word_to_line or end_idx - 1 not in word_to_line:
        return '\n'.join(lines[:5])

    start_line = word_to_line[start_idx][0]
    end_line = word_to_line[end_idx - 1][0]

    # Extrait les lignes entieres
    context_lines = lines[start_line:end_line + 1]

    return '\n'.join(context_lines)


def _validate_unique_answer(song: Song, context_words: list[str], answer_index: int) -> bool:
    """
    Verifie que la reponse est unique dans la chanson.

    Args:
        song: La chanson
        context_words: Les mots du contexte (incluant la reponse)
        answer_index: Index de la reponse dans context_words

    Returns:
        True si la reponse est unique dans ce contexte
    """
    from src.utils.text_processing import normalize_french, extract_words

    # Extrait tous les mots de la chanson (normalises)
    all_words = extract_words(song.full_text)
    normalized_all = [normalize_french(w) for w in all_words]

    # Normalise le contexte et la reponse
    normalized_context = [normalize_french(w) for w in context_words]
    normalized_answer = normalized_context[answer_index]

    # Compte combien de fois cette sequence exacte apparait
    context_len = len(normalized_context)
    matches = 0

    for i in range(len(normalized_all) - context_len + 1):
        window = normalized_all[i:i + context_len]
        if window == normalized_context:
            matches += 1
            if matches > 1:
                return False  # Trouve plus d'une fois = ambigu

    return matches == 1


def _generate_word_puzzle(min_visible_words: int = 5, max_attempts: int = 10) -> Optional[tuple[Song, str, str, WordGuessType]]:
    """
    Genere un puzzle de mot aleatoire avec validation d'unicite.

    Les phrases sont alignees sur les retours a la ligne:
    - NEXT: phrase se termine a une fin de ligne, ___ apres
    - PREVIOUS: phrase commence a un debut de ligne, ___ avant
    - MISSING: phrase complete avec ___ au milieu

    Args:
        min_visible_words: Nombre minimum de mots visibles (sans compter "___")
        max_attempts: Nombre max de tentatives pour trouver un puzzle valide

    Returns:
        Tuple (chanson, phrase_avec_blanc, reponse, type) ou None
    """
    lyrics_service = get_lyrics_service()

    min_total_words = min_visible_words + 1

    for attempt in range(max_attempts):
        # Obtient une phrase aleatoire (deja alignee sur les lignes)
        result = lyrics_service.get_random_phrase(
            min_words=min_total_words,
            max_words=12
        )
        if not result:
            continue

        song, phrase_text, words = result

        if len(words) < min_total_words:
            continue

        # Choisit le type de devinette aleatoirement
        word_type = random.choice(list(WordGuessType))

        if word_type == WordGuessType.NEXT:
            # Mot suivant: la reponse est le DERNIER mot de la phrase
            # On montre tous les mots sauf le dernier + ___
            blank_index = len(words) - 1
            answer = words[blank_index]
            context_words = words[:-1]

            if len(context_words) < min_visible_words:
                continue

            phrase = ' '.join(context_words) + " ___"

        elif word_type == WordGuessType.PREVIOUS:
            # Mot precedent: la reponse est le PREMIER mot de la phrase
            # On montre ___ + tous les mots sauf le premier
            blank_index = 0
            answer = words[blank_index]
            context_words = words[1:]

            if len(context_words) < min_visible_words:
                continue

            phrase = "___ " + ' '.join(context_words)

        else:  # MISSING
            # Mot manquant: on garde toute la phrase, on remplace un mot du milieu
            # Evite le premier et dernier mot pour garder le contexte
            if len(words) < 3:
                continue

            # Choisit un mot au milieu (pas premier ni dernier)
            blank_index = random.randint(1, len(words) - 2)
            answer = words[blank_index]

            # Construit la phrase avec ___
            phrase_words = words.copy()
            phrase_words[blank_index] = "___"
            phrase = ' '.join(phrase_words)

        # Valide que la reponse est unique dans la chanson
        if _validate_unique_answer(song, words, blank_index):
            return song, phrase, answer, word_type

    # Si apres max_attempts on n'a pas trouve de puzzle valide, retourne None
    return None


def start_word_guessing_game(min_visible_words: int = 5) -> Optional[GameSession]:
    """
    Demarre une partie de devinette de mot (5 manches).

    Args:
        min_visible_words: Nombre minimum de mots visibles (sans compter "___")

    Choisit aleatoirement entre: mot suivant, precedent, ou manquant.
    """
    puzzle = _generate_word_puzzle(min_visible_words=min_visible_words)
    if not puzzle:
        return None

    song, phrase, answer, word_type = puzzle

    session = GameSession(
        session_id=_generate_session_id(),
        mode=GameMode.WORD_GUESSING,
        song=song,
        answer=answer,
        phrase=phrase,
        word_type=word_type,
        total_rounds=5,
        current_round=1,
        min_visible_words=min_visible_words,
    )

    _sessions[session.session_id] = session
    return session


def start_song_name_game() -> Optional[GameSession]:
    """
    Demarre une partie de devinette du nom de chanson.

    Affiche un extrait, revele plus a chaque erreur.
    """
    lyrics_service = get_lyrics_service()

    song = lyrics_service.get_random_song()
    if not song:
        return None

    # Divise les paroles en morceaux (indices)
    chunks = split_into_chunks(song.full_text, chunk_size=6)
    if not chunks:
        return None

    # Melange les indices pour plus de variete
    random.shuffle(chunks)

    session = GameSession(
        session_id=_generate_session_id(),
        mode=GameMode.SONG_NAME,
        song=song,
        answer=song.title,
        phrase=chunks[0] if chunks else "",
        all_hints=chunks,
        hints_revealed=1,
    )

    _sessions[session.session_id] = session
    return session


def get_session(session_id: str) -> Optional[GameSession]:
    """Recupere une session par son ID."""
    return _sessions.get(session_id)


def pass_round(session_id: str) -> dict:
    """
    Passe la manche actuelle (compte comme echec).

    Returns:
        Dictionnaire avec le resultat
    """
    session = _sessions.get(session_id)
    if not session:
        return {
            'error': 'Session non trouvee',
            'game_over': True
        }

    if session.game_over:
        return {
            'error': 'Partie terminee',
            'game_over': True
        }

    # Sauvegarde la reponse et contexte avant de passer
    skipped_answer = session.answer
    skipped_song = session.song.title
    skipped_context = _get_answer_context(session.song, session.answer, context_words=20)
    current_round_num = session.current_round

    # Enregistre le resultat de la manche (echec, 0 points)
    session.round_results.append(RoundResult(
        round_number=current_round_num,
        answer=skipped_answer,
        song_title=skipped_song,
        context=skipped_context,
        points=0,
        success=False
    ))

    # Mode word guessing: passer a la manche suivante
    if session.mode == GameMode.WORD_GUESSING and session.current_round < session.total_rounds:
        session.current_round += 1

        # Genere un nouveau puzzle avec le meme min_visible_words
        puzzle = _generate_word_puzzle(min_visible_words=session.min_visible_words)
        if puzzle:
            song, phrase, answer, word_type = puzzle
            session.song = song
            session.phrase = phrase
            session.answer = answer
            session.word_type = word_type
            session.guesses_remaining = 5
            session.guesses_made = []

            return {
                'passed': True,
                'game_over': False,
                'correct_answer': skipped_answer,
                'song_title': skipped_song,
                'answer_context': skipped_context,
                'round_score': 0,
                'current_round': session.current_round,
                'total_rounds': session.total_rounds,
                'cumulative_score': session.cumulative_score,
                'new_phrase': phrase,
                'new_word_type': word_type.value,
                'guesses_remaining': 5,
            }

    # Derniere manche ou mode song : game over
    session.game_over = True
    total_time = time.time() - session.start_time

    # Prepare le recap des manches
    round_results_data = [
        {
            'round': r.round_number,
            'answer': r.answer,
            'song_title': r.song_title,
            'context': r.context,
            'points': r.points,
            'success': r.success
        }
        for r in session.round_results
    ]

    return {
        'passed': True,
        'game_over': True,
        'correct_answer': skipped_answer,
        'song_title': skipped_song,
        'answer_context': skipped_context,
        'round_score': 0,
        'points_earned': session.cumulative_score,
        'time_seconds': round(total_time, 1),
        'current_round': session.current_round,
        'total_rounds': session.total_rounds,
        'round_results': round_results_data,
    }


def reveal_song(session_id: str) -> dict:
    """
    Revele le nom de la chanson (coute 3 tentatives).

    Returns:
        Dictionnaire avec le resultat
    """
    session = _sessions.get(session_id)
    if not session:
        return {
            'error': 'Session non trouvee',
            'game_over': True
        }

    if session.game_over:
        return {
            'error': 'Partie terminee',
            'game_over': True
        }

    # Coute 3 tentatives
    session.guesses_remaining = max(0, session.guesses_remaining - 3)

    if session.guesses_remaining <= 0:
        session.game_over = True
        total_time = time.time() - session.start_time

        return {
            'revealed': True,
            'song_name': session.song.title,
            'game_over': True,
            'guesses_remaining': 0,
            'points_earned': session.cumulative_score,
            'time_seconds': round(total_time, 1),
            'current_round': session.current_round,
            'total_rounds': session.total_rounds,
        }

    return {
        'revealed': True,
        'song_name': session.song.title,
        'game_over': False,
        'guesses_remaining': session.guesses_remaining,
        'current_round': session.current_round,
        'total_rounds': session.total_rounds,
    }


def get_hint_letter_count(session_id: str) -> dict:
    """
    Revele le nombre de lettres dans la reponse (coute 2 tentatives).

    Returns:
        Dictionnaire avec le resultat
    """
    session = _sessions.get(session_id)
    if not session:
        return {'error': 'Session non trouvee', 'game_over': True}

    if session.game_over:
        return {'error': 'Partie terminee', 'game_over': True}

    # Coute 2 tentatives
    session.guesses_remaining = max(0, session.guesses_remaining - 2)

    letter_count = len(session.answer)
    hint_message = str(letter_count)

    if session.guesses_remaining <= 0:
        failed_answer = session.answer
        failed_song = session.song.title

        # Mode word guessing avec manches restantes: passer a la manche suivante
        if session.mode == GameMode.WORD_GUESSING and session.current_round < session.total_rounds:
            session.current_round += 1
            puzzle = _generate_word_puzzle(min_visible_words=session.min_visible_words)
            if puzzle:
                song, phrase, answer, word_type = puzzle
                session.song = song
                session.phrase = phrase
                session.answer = answer
                session.word_type = word_type
                session.guesses_remaining = 5
                session.guesses_made = []

                return {
                    'hint_type': 'letter_count',
                    'hint': hint_message,
                    'round_failed': True,
                    'game_over': False,
                    'correct_answer': failed_answer,
                    'song_title': failed_song,
                    'current_round': session.current_round,
                    'total_rounds': session.total_rounds,
                    'cumulative_score': session.cumulative_score,
                    'new_phrase': phrase,
                    'new_word_type': word_type.value,
                    'guesses_remaining': 5,
                }

        session.game_over = True
        total_time = time.time() - session.start_time

        return {
            'hint_type': 'letter_count',
            'hint': hint_message,
            'game_over': True,
            'guesses_remaining': 0,
            'correct_answer': failed_answer,
            'song_title': failed_song,
            'points_earned': session.cumulative_score,
            'time_seconds': round(total_time, 1),
            'current_round': session.current_round,
            'total_rounds': session.total_rounds,
        }

    return {
        'hint_type': 'letter_count',
        'hint': hint_message,
        'game_over': False,
        'guesses_remaining': session.guesses_remaining,
        'current_round': session.current_round,
        'total_rounds': session.total_rounds,
    }


def get_hint_song_title(session_id: str) -> dict:
    """
    Revele le titre de la chanson (coute 2 tentatives).

    Returns:
        Dictionnaire avec le resultat
    """
    session = _sessions.get(session_id)
    if not session:
        return {'error': 'Session non trouvee', 'game_over': True}

    if session.game_over:
        return {'error': 'Partie terminee', 'game_over': True}

    hint_message = session.song.title

    # Coute 2 tentatives
    session.guesses_remaining = max(0, session.guesses_remaining - 2)

    if session.guesses_remaining <= 0:
        failed_answer = session.answer
        failed_song = session.song.title

        # Mode word guessing avec manches restantes: passer a la manche suivante
        if session.mode == GameMode.WORD_GUESSING and session.current_round < session.total_rounds:
            session.current_round += 1
            puzzle = _generate_word_puzzle(min_visible_words=session.min_visible_words)
            if puzzle:
                song, phrase, answer, word_type = puzzle
                session.song = song
                session.phrase = phrase
                session.answer = answer
                session.word_type = word_type
                session.guesses_remaining = 5
                session.guesses_made = []

                return {
                    'hint_type': 'song_title',
                    'hint': hint_message,
                    'round_failed': True,
                    'game_over': False,
                    'correct_answer': failed_answer,
                    'song_title': failed_song,
                    'current_round': session.current_round,
                    'total_rounds': session.total_rounds,
                    'cumulative_score': session.cumulative_score,
                    'new_phrase': phrase,
                    'new_word_type': word_type.value,
                    'guesses_remaining': 5,
                }

        session.game_over = True
        total_time = time.time() - session.start_time

        return {
            'hint_type': 'song_title',
            'hint': hint_message,
            'game_over': True,
            'guesses_remaining': 0,
            'correct_answer': failed_answer,
            'song_title': failed_song,
            'points_earned': session.cumulative_score,
            'time_seconds': round(total_time, 1),
            'current_round': session.current_round,
            'total_rounds': session.total_rounds,
        }

    return {
        'hint_type': 'song_title',
        'hint': hint_message,
        'song_title': hint_message,
        'game_over': False,
        'guesses_remaining': session.guesses_remaining,
        'current_round': session.current_round,
        'total_rounds': session.total_rounds,
    }


def get_hint_first_letter(session_id: str) -> dict:
    """
    Revele la premiere lettre de la reponse (coute 2 tentatives).

    Returns:
        Dictionnaire avec le resultat
    """
    session = _sessions.get(session_id)
    if not session:
        return {'error': 'Session non trouvee', 'game_over': True}

    if session.game_over:
        return {'error': 'Partie terminee', 'game_over': True}

    # Coute 2 tentatives
    session.guesses_remaining = max(0, session.guesses_remaining - 2)

    first_letter = session.answer[0].upper() if session.answer else ''
    hint_message = first_letter

    if session.guesses_remaining <= 0:
        failed_answer = session.answer
        failed_song = session.song.title

        # Mode word guessing avec manches restantes: passer a la manche suivante
        if session.mode == GameMode.WORD_GUESSING and session.current_round < session.total_rounds:
            session.current_round += 1
            puzzle = _generate_word_puzzle(min_visible_words=session.min_visible_words)
            if puzzle:
                song, phrase, answer, word_type = puzzle
                session.song = song
                session.phrase = phrase
                session.answer = answer
                session.word_type = word_type
                session.guesses_remaining = 5
                session.guesses_made = []

                return {
                    'hint_type': 'first_letter',
                    'hint': hint_message,
                    'round_failed': True,
                    'game_over': False,
                    'correct_answer': failed_answer,
                    'song_title': failed_song,
                    'current_round': session.current_round,
                    'total_rounds': session.total_rounds,
                    'cumulative_score': session.cumulative_score,
                    'new_phrase': phrase,
                    'new_word_type': word_type.value,
                    'guesses_remaining': 5,
                }

        session.game_over = True
        total_time = time.time() - session.start_time

        return {
            'hint_type': 'first_letter',
            'hint': hint_message,
            'game_over': True,
            'guesses_remaining': 0,
            'correct_answer': failed_answer,
            'song_title': failed_song,
            'points_earned': session.cumulative_score,
            'time_seconds': round(total_time, 1),
            'current_round': session.current_round,
            'total_rounds': session.total_rounds,
        }

    return {
        'hint_type': 'first_letter',
        'hint': hint_message,
        'game_over': False,
        'guesses_remaining': session.guesses_remaining,
        'current_round': session.current_round,
        'total_rounds': session.total_rounds,
    }


def make_guess(session_id: str, guess: str) -> dict:
    """
    Soumet une reponse.

    Returns:
        Dictionnaire avec le resultat
    """
    session = _sessions.get(session_id)
    if not session:
        return {
            'error': 'Session non trouvee',
            'game_over': True
        }

    if session.game_over:
        return {
            'error': 'Partie terminee',
            'game_over': True,
            'correct_answer': session.answer,
            'song_title': session.song.title
        }

    # Enregistre la tentative
    session.guesses_made.append(guess)
    session.guesses_remaining -= 1

    # Verifie la reponse
    is_correct = words_match(guess, session.answer)

    if is_correct:
        # Calcule le score pour cette manche
        # Utilise le temps total depuis le debut de la partie
        total_time = time.time() - session.start_time
        guesses_used = len(session.guesses_made)
        round_score = calculate_score(True, guesses_used, total_time)
        session.cumulative_score += round_score

        # Extrait le contexte etendu pour affichage
        answer_context = _get_answer_context(session.song, session.answer, context_words=20)
        current_song_title = session.song.title
        current_answer = session.answer
        current_round_num = session.current_round

        # Enregistre le resultat de la manche (succes)
        session.round_results.append(RoundResult(
            round_number=current_round_num,
            answer=current_answer,
            song_title=current_song_title,
            context=answer_context,
            points=round_score,
            success=True
        ))

        # Mode word guessing: passer a la manche suivante si pas termine
        if session.mode == GameMode.WORD_GUESSING and session.current_round < session.total_rounds:
            session.current_round += 1

            # Genere un nouveau puzzle avec le meme min_visible_words
            puzzle = _generate_word_puzzle(min_visible_words=session.min_visible_words)
            if puzzle:
                song, phrase, answer, word_type = puzzle
                session.song = song
                session.phrase = phrase
                session.answer = answer
                session.word_type = word_type
                session.guesses_remaining = 5
                session.guesses_made = []

                return {
                    'correct': True,
                    'round_complete': True,
                    'game_over': False,
                    'current_round': session.current_round,
                    'total_rounds': session.total_rounds,
                    'round_score': round_score,
                    'cumulative_score': session.cumulative_score,
                    'new_phrase': phrase,
                    'new_word_type': word_type.value,
                    'guesses_remaining': 5,
                    'correct_answer': current_answer,
                    'song_title': current_song_title,
                    'answer_context': answer_context,
                }

        # Partie terminee (toutes les manches ou mode song)
        session.game_over = True
        session.correct = True
        total_time = time.time() - session.start_time

        # Prepare le recap des manches
        round_results_data = [
            {
                'round': r.round_number,
                'answer': r.answer,
                'song_title': r.song_title,
                'context': r.context,
                'points': r.points,
                'success': r.success
            }
            for r in session.round_results
        ]

        return {
            'correct': True,
            'game_over': True,
            'round_complete': True,
            'guesses_remaining': session.guesses_remaining,
            'points_earned': session.cumulative_score,
            'round_score': round_score,
            'correct_answer': current_answer,
            'song_title': current_song_title,
            'answer_context': answer_context,
            'time_seconds': round(total_time, 1),
            'current_round': session.current_round,
            'total_rounds': session.total_rounds,
            'round_results': round_results_data,
        }

    # Mauvaise reponse - plus de tentatives
    if session.guesses_remaining <= 0:
        failed_answer = session.answer
        failed_song = session.song.title
        failed_context = _get_answer_context(session.song, session.answer, context_words=20)
        current_round_num = session.current_round

        # Enregistre le resultat de la manche (echec)
        session.round_results.append(RoundResult(
            round_number=current_round_num,
            answer=failed_answer,
            song_title=failed_song,
            context=failed_context,
            points=0,
            success=False
        ))

        # Mode word guessing avec manches restantes: passer a la manche suivante
        if session.mode == GameMode.WORD_GUESSING and session.current_round < session.total_rounds:
            session.current_round += 1

            # Genere un nouveau puzzle
            puzzle = _generate_word_puzzle(min_visible_words=session.min_visible_words)
            if puzzle:
                song, phrase, answer, word_type = puzzle
                session.song = song
                session.phrase = phrase
                session.answer = answer
                session.word_type = word_type
                session.guesses_remaining = 5
                session.guesses_made = []

                return {
                    'correct': False,
                    'round_failed': True,
                    'game_over': False,
                    'correct_answer': failed_answer,
                    'song_title': failed_song,
                    'answer_context': failed_context,
                    'round_score': 0,
                    'current_round': session.current_round,
                    'total_rounds': session.total_rounds,
                    'cumulative_score': session.cumulative_score,
                    'new_phrase': phrase,
                    'new_word_type': word_type.value,
                    'guesses_remaining': 5,
                }

        # Derniere manche ou mode song: game over
        session.game_over = True
        total_time = time.time() - session.start_time

        # Prepare le recap des manches
        round_results_data = [
            {
                'round': r.round_number,
                'answer': r.answer,
                'song_title': r.song_title,
                'context': r.context,
                'points': r.points,
                'success': r.success
            }
            for r in session.round_results
        ]

        return {
            'correct': False,
            'game_over': True,
            'guesses_remaining': 0,
            'points_earned': session.cumulative_score,
            'correct_answer': failed_answer,
            'song_title': failed_song,
            'answer_context': failed_context,
            'round_score': 0,
            'time_seconds': round(total_time, 1),
            'current_round': session.current_round,
            'total_rounds': session.total_rounds,
            'round_results': round_results_data,
        }

    # Encore des tentatives - revele un indice pour le mode chanson
    hint = None
    if session.mode == GameMode.SONG_NAME:
        if session.hints_revealed < len(session.all_hints):
            session.hints_revealed += 1
            # Construit la phrase avec tous les indices reveles
            revealed_hints = session.all_hints[:session.hints_revealed]
            session.phrase = ' / '.join(revealed_hints)
            hint = session.phrase

    return {
        'correct': False,
        'game_over': False,
        'guesses_remaining': session.guesses_remaining,
        'hint': hint,
        'phrase': session.phrase,
        'current_round': session.current_round,
        'total_rounds': session.total_rounds,
    }


def cleanup_old_sessions(max_age_seconds: int = 3600) -> int:
    """
    Nettoie les sessions anciennes.

    Args:
        max_age_seconds: Age maximum en secondes

    Returns:
        Nombre de sessions supprimees
    """
    now = time.time()
    to_remove = []

    for session_id, session in _sessions.items():
        if now - session.start_time > max_age_seconds:
            to_remove.append(session_id)

    for session_id in to_remove:
        del _sessions[session_id]

    return len(to_remove)


def get_active_sessions_count() -> int:
    """Retourne le nombre de sessions actives."""
    return len(_sessions)
