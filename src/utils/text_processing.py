"""
Utilitaires de traitement de texte francais.
Normalisation et comparaison tolerante.
"""

import unicodedata
import re


# Liste des mots vides (stopwords) francais courants
FRENCH_STOPWORDS = {
    # Articles
    'le', 'la', 'les', 'un', 'une', 'des', 'du', 'au', 'aux',
    # Pronoms
    'je', 'tu', 'il', 'elle', 'on', 'nous', 'vous', 'ils', 'elles',
    'me', 'te', 'se', 'moi', 'toi', 'lui', 'leur', 'leurs',
    'ce', 'ca', 'ceci', 'cela',
    # Prepositions
    'de', 'a', 'en', 'par', 'pour', 'sans', 'avec', 'dans', 'sur', 'sous',
    'vers', 'chez', 'contre', 'entre', 'pendant', 'depuis',
    # Conjonctions
    'et', 'ou', 'mais', 'donc', 'or', 'ni', 'car', 'que', 'qui', 'quoi',
    'si', 'comme', 'quand', 'lorsque',
    # Adverbes courants
    'ne', 'pas', 'plus', 'non', 'oui', 'si', 'bien', 'mal', 'tres',
    'peu', 'trop', 'tout', 'tous', 'toute', 'toutes', 'rien',
    # Verbes auxiliaires et etre/avoir courants
    'est', 'sont', 'etait', 'etaient', 'ete', 'etre',
    'ai', 'as', 'a', 'ont', 'avait', 'avaient', 'avoir', 'eu',
    # Autres mots tres courants
    'y', 'en', 'dont', 'où', 'ou',
}


def normalize_french(text: str) -> str:
    """
    Normalise le texte francais pour comparaison.

    - Convertit en minuscules
    - Supprime les accents
    - Supprime la ponctuation (sauf apostrophes)
    - Normalise les espaces
    """
    # Minuscules
    text = text.lower()

    # Supprime les accents
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')

    # Remplace tous les types d'apostrophes par des apostrophes simples
    # U+2018 ('), U+2019 ('), U+00B4 (´), U+0060 (`)
    text = text.replace("\u2018", "'").replace("\u2019", "'").replace("\u00B4", "'").replace("\u0060", "'")

    # Supprime la ponctuation sauf apostrophes
    text = re.sub(r"[^\w\s']", '', text)

    # Normalise les espaces
    text = ' '.join(text.split())

    return text


def words_match(guess: str, answer: str) -> bool:
    """
    Verifie si la reponse correspond (tolerant aux accents et casse).

    Args:
        guess: La reponse du joueur
        answer: La bonne reponse

    Returns:
        True si les mots correspondent
    """
    return normalize_french(guess) == normalize_french(answer)


def extract_words(text: str) -> list[str]:
    """
    Extrait les mots d'un texte.

    Garde les mots avec apostrophes intacts (ex: "l'amour", "qu'il").
    """
    # Nettoie le texte - remplace tous les types d'apostrophes par '
    # U+2018 ('), U+2019 ('), U+00B4 (´), U+0060 (`)
    text = text.replace("\u2018", "'").replace("\u2019", "'").replace("\u00B4", "'").replace("\u0060", "'")

    # Supprime la ponctuation sauf apostrophes
    text = re.sub(r"[^\w\s']", ' ', text)

    # Split et filtre les mots vides
    words = [w.strip() for w in text.split() if w.strip()]

    return words


def create_phrase_with_blank(words: list[str], blank_index: int, context_size: int = 3) -> tuple[str, str]:
    """
    Cree une phrase avec un mot manquant.

    Args:
        words: Liste de mots
        blank_index: Index du mot a cacher
        context_size: Nombre de mots de contexte de chaque cote

    Returns:
        Tuple (phrase_avec_blanc, mot_cache)
    """
    if blank_index < 0 or blank_index >= len(words):
        raise ValueError(f"Index {blank_index} hors limites pour {len(words)} mots")

    start = max(0, blank_index - context_size)
    end = min(len(words), blank_index + context_size + 1)

    phrase_words = words[start:end]
    relative_blank = blank_index - start

    answer = phrase_words[relative_blank]
    phrase_words[relative_blank] = "___"

    phrase = ' '.join(phrase_words)
    return phrase, answer


def split_into_chunks(text: str, chunk_size: int = 6) -> list[str]:
    """
    Divise le texte en morceaux de taille approximative.

    Args:
        text: Texte complet
        chunk_size: Nombre approximatif de mots par morceau

    Returns:
        Liste de morceaux de texte
    """
    words = extract_words(text)
    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)

    return chunks


def is_stopword(word: str) -> bool:
    """
    Verifie si un mot est un stopword (mot vide).

    Args:
        word: Le mot a verifier

    Returns:
        True si le mot est un stopword
    """
    normalized = normalize_french(word)
    return normalized in FRENCH_STOPWORDS
