FROM --platform=linux/arm64 ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY deploy/requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

COPY backend/ ./backend/
COPY data/ ./data/
COPY deploy/entrypoint.py ./entrypoint.py

ENV USE_BEDROCK=true

EXPOSE 9000
CMD ["python", "entrypoint.py"]
