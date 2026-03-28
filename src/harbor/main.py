"""Entrypoint — run with: uvicorn harbor.main:app"""

from mangum import Mangum

from harbor.api.routes import create_app

app = create_app()
handler = Mangum(app, lifespan="off")
