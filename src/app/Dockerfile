# Backend image — FastAPI demo API (MOCK_MODE by default)
FROM python:3.13-slim

# uv for fast, reproducible installs
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /srv

COPY pyproject.toml ./
COPY src ./src
COPY data ./data

RUN uv sync --no-dev

ENV MOCK_MODE=true
EXPOSE 8080

CMD ["uv", "run", "uvicorn", "app.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8080"]
