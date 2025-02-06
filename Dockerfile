FROM python:3.12.8-slim-bookworm as builder

RUN pip install --no-cache-dir poetry==2.0.1

ENV POETRY_VIRTUALENVS_IN_PROJECT=true \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN --mount=type=cache,target=~/.cache/pypoetry poetry install --no-root

FROM python:3.12.8-slim-bookworm

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY --from=builder /app/.venv .venv

COPY . .