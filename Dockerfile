# Build stage
FROM python:3.12.8-slim-bookworm as builder

ENV POETRY_VERSION=2.0.1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_HOME=/etc/poetry
ENV PATH=$POETRY_HOME/bin:$PATH
RUN apt update && apt install -y --no-install-recommends curl
RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install


# Runtime stage
FROM python:3.12.8-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY --from=builder /app/.venv .venv
COPY . .

ENTRYPOINT [".venv/bin/python", "bot.py"]
