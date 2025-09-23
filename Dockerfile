# Build stage
FROM python:3.13-slim AS base

ENV POETRY_HOME=/opt/poetry
ENV PATH="$POETRY_HOME/bin:$PATH" \
    POETRY_VIRTUALENVS_IN_PROJECT=true

RUN python3 -m venv $POETRY_HOME \
    && $POETRY_HOME/bin/pip install --no-cache-dir -U pip setuptools \
    && $POETRY_HOME/bin/pip install --no-cache-dir "poetry>=2,<3"

WORKDIR /app

COPY pyproject.toml poetry.lock* /app/
RUN poetry install --only main


# Runtime stage
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app
COPY --from=builder /app/.venv .venv
COPY . .

CMD ["python", "bot.py"]
