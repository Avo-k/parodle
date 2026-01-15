# Parodle

Jeu de devinette de paroles de chansons en francais.

## Installation

### Prerequis

- Python 3.12 ou superieur
- [uv](https://docs.astral.sh/uv/) - gestionnaire de paquets Python

Pour installer uv :

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Configuration

1. Clonez le depot :

```bash
git clone https://github.com/Avo-k/parodle.git
cd parodle
```

2. Les dependances seront automatiquement installees lors du premier `uv run`

## Lancer le jeu

```bash
uv run uvicorn src.main:app --reload
```

Puis ouvrez http://localhost:8000 dans votre navigateur.

## Modes de jeu

### 1. Deviner le mot (5 manches)

Trouvez le mot manquant dans une phrase extraite des paroles de l'artiste choisi.
- **5 manches** pour maximiser votre score
- **3 variantes** choisies aleatoirement :
  - Mot suivant : "Ne me quitte ___"
  - Mot precedent : "___ me quitte pas"
  - Mot manquant : "Ne ___ quitte pas"
- **5 tentatives** par manche
- Score cumulatif sur les 5 manches
- **5 mots visibles minimum** (sans compter "___") - configurable au demarrage

### 2. Deviner la chanson

Trouvez le titre de la chanson a partir d'un extrait.
- Chaque mauvaise reponse revele un vers supplementaire
- 5 tentatives maximum

## Systeme de points

```
Score par manche = 1000 × multiplicateur_tentatives × multiplicateur_temps
```

- **Tentatives** : 1ere = 100%, chaque erreur = -15%
- **Temps** : < 10s = 100%, puis diminue (min 30%)

**Mode "Deviner le mot"** : Score total = somme des 5 manches

## Caracteristiques

- **Multi-artistes** : Choisissez parmi plusieurs artistes
  - Jacques Brel (120 chansons)
  - Bénabar (104 chansons)
- **Comparaison tolerante** : les accents sont affiches mais pas requis dans vos reponses
- **Interface minimaliste** en francais
- **Timer** pour chaque partie
- **Nombre de mots configurable** : Ajustez le nombre minimum de mots visibles (par defaut : 5)

## Parametres API

Lors du demarrage d'une partie via `POST /api/game/start` :

```json
{
  "mode": "word_guessing",
  "artist_id": "jacques-brel",
  "min_visible_words": 5
}
```

- `mode` : Mode de jeu ("word_guessing" ou "song_name")
- `artist_id` : Identifiant de l'artiste ("jacques-brel" ou "benabar")
- `min_visible_words` : Nombre minimum de mots visibles (sans compter "___")
  - **3** : Plus difficile, moins de contexte
  - **5** : Par defaut, equilibre difficulte/contexte
  - **8** : Plus facile, plus de contexte

## Scraping des paroles

Pour re-scraper les paroles (si besoin) :

**Jacques Brel** :
```bash
uv run -m scripts.scrape_lyrics
```

**Bénabar** :
```bash
uv run -m scripts.scrape_benabar
```

Les paroles sont recuperees depuis paroles.net et sauvegardees dans `data/artists/{artiste}.json`.

## Structure du projet

```
parodle/
├── data/
│   ├── artists/              # Paroles par artiste
│   │   ├── jacques-brel.json # 120 chansons de Brel
│   │   └── benabar.json      # 104 chansons de Bénabar
│   └── artists.json          # Metadata des artistes
├── scripts/
│   ├── scrape_lyrics.py      # Script de scraping Brel
│   └── scrape_benabar.py     # Script de scraping Bénabar
├── src/
│   ├── main.py              # App FastAPI
│   ├── routers/game.py      # API endpoints
│   ├── services/            # Logique de jeu
│   │   ├── game_service.py
│   │   ├── lyrics_service.py
│   │   └── scoring_service.py
│   ├── schemas/             # Schemas Pydantic
│   └── utils/               # Normalisation texte
└── static/                  # Frontend HTML/CSS/JS
```

## API Endpoints

- `GET /` - Page d'accueil
- `GET /health` - Verification de sante
- `GET /api/game/artists` - Liste des artistes disponibles
- `POST /api/game/start` - Demarrer une partie
- `POST /api/game/guess` - Soumettre une reponse
- `GET /api/game/session/{id}` - Etat d'une session
- `GET /api/game/stats` - Statistiques

## Technologies

- **Backend** : FastAPI, Python 3.12
- **Frontend** : HTML5, CSS3, JavaScript vanilla
- **Package manager** : UV
- **Data** : JSON (224 chansons au total)
