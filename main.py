"""
Point d'entree pour lancer l'application.
Usage: uv run python main.py
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
