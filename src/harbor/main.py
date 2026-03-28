"""Entrypoint — run with: uvicorn harbor.main:app"""

from harbor.api.routes import create_app

app = create_app()
