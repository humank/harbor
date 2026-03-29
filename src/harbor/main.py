"""Entrypoint — composition root. No business logic here."""

from mangum import Mangum

from harbor.api.deps import Services
from harbor.api.routes import create_app

services = Services()
app = create_app(services)
handler = Mangum(app, lifespan="off")
