# Documentation technique - Parodle

## Choix du nombre de mots

### Paramètres actuels

```python
get_random_phrase(min_words=8, max_words=15)
```

### Justification

**8 mots minimum** :
- Assez de contexte pour que la phrase ait du sens
- Permet de valider l'unicité de la réponse dans la chanson
- Équilibre entre difficulté et faisabilité

**15 mots maximum** :
- Phrase pas trop longue pour tenir sur mobile
- Le joueur peut lire et mémoriser la phrase facilement
- Évite de révéler trop de paroles d'un coup

### Impact sur la difficulté

- **Phrases courtes** (8-10 mots) : Plus difficile, moins de contexte
- **Phrases longues** (12-15 mots) : Plus facile, plus d'indices

Le système choisit **aléatoirement** entre min et max pour varier la difficulté.

---

## Validation d'unicité

### Problème résolu

Avant : Une phrase comme "la la la ___" pouvait avoir plusieurs réponses si "la la la" apparaissait plusieurs fois dans la chanson avec des mots différents après.

Maintenant : On vérifie que la **séquence complète** de mots (incluant la réponse) n'apparaît qu'**une seule fois** dans toute la chanson.

### Algorithme

```python
def _validate_unique_answer(song, context_words, answer_index):
    # 1. Extrait tous les mots de la chanson (normalisés)
    # 2. Cherche combien de fois la séquence complète apparaît
    # 3. Retourne True seulement si trouvé exactement 1 fois
```

### Mécanisme de retry

Si un puzzle n'est pas unique :
- **max_attempts = 10** : Essaie jusqu'à 10 phrases différentes
- Retourne `None` si aucune phrase valide n'est trouvée après 10 essais
- En pratique, trouve presque toujours une phrase valide en 1-3 essais

---

## Traitement du texte

### Apostrophes

Les apostrophes typographiques (`'` et `'`) sont normalisées en apostrophes standards (`'`) :

```python
text.replace("'", "'").replace("'", "'")
```

**Dans l'affichage** : Garde les apostrophes originales (ex: "l'amour", "qu'il")
**Dans la comparaison** : Normalise pour accepter "l amour" ou "l'amour"

### Accents

**Dans l'affichage** : Accents préservés (ex: "café", "où")
**Dans la comparaison** : Accents retirés pour tolérance

```python
# Joueur tape "cafe" → accepté pour "café"
# Joueur tape "ou" → accepté pour "où"
```

### Retours à la ligne

**Actuellement** : Les retours à la ligne (`\n`) sont **supprimés** lors de l'extraction.

**Raison** :
- Phrases de jeu sont des fragments courts (8-15 mots)
- Structure en ligne unique plus adaptée au mobile
- Focus sur la devinette de mots, pas de vers entiers

**Alternative** : Pourrait être modifié pour préserver les `\n` dans l'affichage, mais complexifierait le système de validation d'unicité.

---

## Système de scoring

### Formule

```
Score = 1000 × multiplicateur_tentatives × multiplicateur_temps
```

### Multiplicateurs

**Tentatives** :
- 1ère tentative : 100%
- 2ème tentative : 85%
- 3ème tentative : 70%
- 4ème tentative : 55%
- 5ème tentative : 40%

**Temps** :
- < 10 secondes : 100%
- 10-120 secondes : Décroissance logarithmique de 100% à 30%
- > 120 secondes : 30% (minimum)

### Mode 5 manches

Score total = Somme des scores de chaque manche
- Score maximum théorique : 5000 points (5 × 1000)
- Chaque manche est indépendante (nouveau timer, 5 nouvelles tentatives)

---

## Performance

### Métriques

- **120 chansons** chargées en mémoire (~2-3 MB)
- **Génération de puzzle** : ~5-15ms (avec validation)
- **Validation d'unicité** : O(n) où n = nombre de mots dans la chanson
- **Sessions en mémoire** : Dict Python (aucune persistance)

### Nettoyage automatique

Les sessions anciennes (>1h) pourraient être nettoyées périodiquement (pas implémenté actuellement car usage faible prévu).
