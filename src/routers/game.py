"""
Routes API pour le jeu.
"""

from fastapi import APIRouter, HTTPException

from src.schemas.game import (
    StartGameRequest,
    StartGameResponse,
    GuessRequest,
    GuessResponse,
    PassRequest,
    RevealRequest,
    HintRequest,
    SessionState,
    StatsResponse,
    GameMode,
    WordGuessType,
)
from src.services.game_service import (
    start_word_guessing_game,
    start_song_name_game,
    get_session,
    make_guess,
    pass_round,
    reveal_song,
    get_hint_letter_count,
    get_hint_song_title,
    get_hint_first_letter,
    get_active_sessions_count,
)
from src.services.lyrics_service import get_lyrics_service

router = APIRouter(prefix="/api/game", tags=["game"])


@router.post("/start", response_model=StartGameResponse)
async def start_game(request: StartGameRequest) -> StartGameResponse:
    """
    Demarre une nouvelle partie.

    - **mode**: "word_guessing" ou "song_name"
    - **min_visible_words**: Nombre minimum de mots visibles (par defaut 5)
    """
    if request.mode == GameMode.WORD_GUESSING:
        session = start_word_guessing_game(min_visible_words=request.min_visible_words)
    else:
        session = start_song_name_game()

    if not session:
        raise HTTPException(
            status_code=500,
            detail="Impossible de creer une partie. Verifiez que les paroles sont chargees."
        )

    return StartGameResponse(
        session_id=session.session_id,
        mode=GameMode(session.mode.value),
        phrase=session.phrase,
        word_type=WordGuessType(session.word_type.value) if session.word_type else None,
        max_guesses=5,
        current_round=session.current_round,
        total_rounds=session.total_rounds,
    )


@router.post("/guess", response_model=GuessResponse)
async def submit_guess(request: GuessRequest) -> GuessResponse:
    """
    Soumet une reponse.

    - **session_id**: ID de la session
    - **guess**: La reponse du joueur
    """
    result = make_guess(request.session_id, request.guess)

    if 'error' in result and result.get('error') == 'Session non trouvee':
        raise HTTPException(status_code=404, detail="Session non trouvee")

    return GuessResponse(
        correct=result.get('correct', False),
        game_over=result.get('game_over', False),
        guesses_remaining=result.get('guesses_remaining', 0),
        points_earned=result.get('points_earned'),
        correct_answer=result.get('correct_answer'),
        song_title=result.get('song_title'),
        hint=result.get('hint'),
        phrase=result.get('phrase'),
        time_seconds=result.get('time_seconds'),
        error=result.get('error'),
        round_complete=result.get('round_complete'),
        round_failed=result.get('round_failed'),
        current_round=result.get('current_round'),
        total_rounds=result.get('total_rounds'),
        round_score=result.get('round_score'),
        cumulative_score=result.get('cumulative_score'),
        new_phrase=result.get('new_phrase'),
        new_word_type=result.get('new_word_type'),
        answer_context=result.get('answer_context'),
        round_results=result.get('round_results'),
    )


@router.post("/pass")
async def pass_current_round(request: PassRequest) -> GuessResponse:
    """
    Passe le mot actuel (passe a la manche suivante sans points).

    - **session_id**: ID de la session
    """
    result = pass_round(request.session_id)

    if 'error' in result and result.get('error') == 'Session non trouvee':
        raise HTTPException(status_code=404, detail="Session non trouvee")

    return GuessResponse(
        correct=False,
        game_over=result.get('game_over', False),
        guesses_remaining=result.get('guesses_remaining', 0),
        points_earned=result.get('points_earned'),
        correct_answer=result.get('correct_answer'),
        song_title=result.get('song_title'),
        answer_context=result.get('answer_context'),
        time_seconds=result.get('time_seconds'),
        round_complete=result.get('passed'),
        round_score=result.get('round_score'),
        current_round=result.get('current_round'),
        total_rounds=result.get('total_rounds'),
        cumulative_score=result.get('cumulative_score'),
        new_phrase=result.get('new_phrase'),
        new_word_type=result.get('new_word_type'),
        round_results=result.get('round_results'),
    )


@router.post("/reveal")
async def reveal_song_name(request: RevealRequest) -> GuessResponse:
    """
    Revele le nom de la chanson (coute 3 tentatives).

    - **session_id**: ID de la session
    """
    result = reveal_song(request.session_id)

    if 'error' in result and result.get('error') == 'Session non trouvee':
        raise HTTPException(status_code=404, detail="Session non trouvee")

    return GuessResponse(
        correct=False,
        game_over=result.get('game_over', False),
        guesses_remaining=result.get('guesses_remaining', 0),
        points_earned=result.get('points_earned'),
        time_seconds=result.get('time_seconds'),
        song_title=result.get('song_name'),
        current_round=result.get('current_round'),
        total_rounds=result.get('total_rounds'),
    )


@router.post("/hint/letter-count")
async def hint_letter_count(request: HintRequest) -> GuessResponse:
    """
    Revele le nombre de lettres dans la reponse (coute 2 tentatives).

    - **session_id**: ID de la session
    """
    result = get_hint_letter_count(request.session_id)

    if 'error' in result and result.get('error') == 'Session non trouvee':
        raise HTTPException(status_code=404, detail="Session non trouvee")

    return GuessResponse(
        correct=False,
        game_over=result.get('game_over', False),
        guesses_remaining=result.get('guesses_remaining', 0),
        points_earned=result.get('points_earned'),
        correct_answer=result.get('correct_answer'),
        song_title=result.get('song_title'),
        time_seconds=result.get('time_seconds'),
        hint=result.get('hint'),
        round_failed=result.get('round_failed'),
        current_round=result.get('current_round'),
        total_rounds=result.get('total_rounds'),
        cumulative_score=result.get('cumulative_score'),
        new_phrase=result.get('new_phrase'),
        new_word_type=result.get('new_word_type'),
    )


@router.post("/hint/song-title")
async def hint_song_title(request: HintRequest) -> GuessResponse:
    """
    Revele le titre de la chanson (coute 2 tentatives).

    - **session_id**: ID de la session
    """
    result = get_hint_song_title(request.session_id)

    if 'error' in result and result.get('error') == 'Session non trouvee':
        raise HTTPException(status_code=404, detail="Session non trouvee")

    return GuessResponse(
        correct=False,
        game_over=result.get('game_over', False),
        guesses_remaining=result.get('guesses_remaining', 0),
        points_earned=result.get('points_earned'),
        correct_answer=result.get('correct_answer'),
        song_title=result.get('song_title'),
        time_seconds=result.get('time_seconds'),
        hint=result.get('hint'),
        round_failed=result.get('round_failed'),
        current_round=result.get('current_round'),
        total_rounds=result.get('total_rounds'),
        cumulative_score=result.get('cumulative_score'),
        new_phrase=result.get('new_phrase'),
        new_word_type=result.get('new_word_type'),
    )


@router.post("/hint/first-letter")
async def hint_first_letter(request: HintRequest) -> GuessResponse:
    """
    Revele la premiere lettre de la reponse (coute 2 tentatives).

    - **session_id**: ID de la session
    """
    result = get_hint_first_letter(request.session_id)

    if 'error' in result and result.get('error') == 'Session non trouvee':
        raise HTTPException(status_code=404, detail="Session non trouvee")

    return GuessResponse(
        correct=False,
        game_over=result.get('game_over', False),
        guesses_remaining=result.get('guesses_remaining', 0),
        points_earned=result.get('points_earned'),
        correct_answer=result.get('correct_answer'),
        song_title=result.get('song_title'),
        time_seconds=result.get('time_seconds'),
        hint=result.get('hint'),
        round_failed=result.get('round_failed'),
        current_round=result.get('current_round'),
        total_rounds=result.get('total_rounds'),
        cumulative_score=result.get('cumulative_score'),
        new_phrase=result.get('new_phrase'),
        new_word_type=result.get('new_word_type'),
    )


@router.get("/session/{session_id}", response_model=SessionState)
async def get_session_state(session_id: str) -> SessionState:
    """
    Recupere l'etat d'une session.
    """
    session = get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvee")

    return SessionState(
        session_id=session.session_id,
        mode=GameMode(session.mode.value),
        phrase=session.phrase,
        word_type=WordGuessType(session.word_type.value) if session.word_type else None,
        guesses_remaining=session.guesses_remaining,
        game_over=session.game_over,
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats() -> StatsResponse:
    """
    Retourne les statistiques du jeu.
    """
    lyrics_service = get_lyrics_service()

    return StatsResponse(
        total_songs=lyrics_service.count_songs(),
        active_sessions=get_active_sessions_count(),
    )
