"""
Application FastAPI pour Parodle - Jeu de paroles Jacques Brel.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from src.routers.game import router as game_router
from src.services.lyrics_service import get_lyrics_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application."""
    # Startup: charge les paroles
    print("Demarrage de Parodle...")
    lyrics_service = get_lyrics_service()
    print(f"Paroles chargees: {lyrics_service.count_songs()} chansons")
    yield
    # Shutdown
    print("Arret de Parodle...")


app = FastAPI(
    title="Parodle",
    description="Jeu de devinette de paroles de Jacques Brel",
    version="1.0.0",
    lifespan=lifespan,
)

# Inclut les routes API
app.include_router(game_router)

# Monte les fichiers statiques
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/")
async def root():
    """Sert la page d'accueil."""
    index_path = static_path / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Bienvenue sur Parodle!", "status": "ok"}


@app.get("/health")
async def health():
    """Endpoint de verification de sante."""
    lyrics_service = get_lyrics_service()
    return {
        "status": "ok",
        "songs_loaded": lyrics_service.count_songs()
    }
