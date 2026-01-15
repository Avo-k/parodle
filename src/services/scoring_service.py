"""
Service de calcul des scores.
"""

import math


def calculate_score(
    correct: bool,
    guesses_used: int,
    time_seconds: float,
    max_guesses: int = 5,
    base_points: int = 1000
) -> int:
    """
    Calcule le score final.

    Args:
        correct: Si la reponse est correcte
        guesses_used: Nombre de tentatives utilisees (1-5)
        time_seconds: Temps ecoule en secondes
        max_guesses: Nombre maximum de tentatives
        base_points: Points de base

    Returns:
        Score final (0 si incorrect)
    """
    if not correct:
        return 0

    # Multiplicateur tentatives: 1ere = 100%, chaque erreur = -15%
    # guesses_used = 1 -> 1.0, 2 -> 0.85, 3 -> 0.70, 4 -> 0.55, 5 -> 0.40
    guess_multiplier = 1.0 - (guesses_used - 1) * 0.15
    guess_multiplier = max(0.25, guess_multiplier)  # Minimum 25%

    # Pas de penalite de temps pour l'instant
    time_multiplier = 1.0

    final_score = int(base_points * guess_multiplier * time_multiplier)

    return final_score


def format_score_breakdown(
    score: int,
    guesses_used: int,
    time_seconds: float
) -> dict:
    """
    Retourne le detail du calcul du score.

    Returns:
        Dictionnaire avec les details
    """
    guess_multiplier = max(0.25, 1.0 - (guesses_used - 1) * 0.15)

    if time_seconds <= 10:
        time_multiplier = 1.0
    else:
        decay = math.log(time_seconds / 10 + 1) / math.log(13)
        time_multiplier = max(0.3, 1.0 - decay * 0.7)

    return {
        'score': score,
        'base_points': 1000,
        'guess_multiplier': round(guess_multiplier, 2),
        'time_multiplier': round(time_multiplier, 2),
        'guesses_used': guesses_used,
        'time_seconds': round(time_seconds, 1)
    }
