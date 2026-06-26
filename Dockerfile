# Multi-stage build overview:
#
#   base            Python + C build tools (gcc, postgresql-dev, etc.)
#   ├─ final-builder  poetry install (prod deps only) → compiled venv
#   └─ tests-builder  poetry install (prod + test deps) → compiled venv
#
#   base-small      Clean Python image + minimal runtime libs + non-root user
#   ├─ final        Copies venv from final-builder. Production image.
#   └─ tests        Copies venv from tests-builder. CI/testing image.
#
# C extensions (asyncpg, psycopg2, pydantic-core) are compiled in the builder
# stages where gcc is available, then copied as pre-built .so files into the
# clean runtime images — no compiler needed at runtime.

ARG TARGETPLATFORM=linux/amd64

# -----------------------------------------------------------------------------
# base: shared build environment for both builder stages.
# Contains C compilers and headers required to compile Python extensions.
# Not used directly at runtime.
# -----------------------------------------------------------------------------
FROM --platform=$TARGETPLATFORM python:3.13-alpine3.21 AS base

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/dependencies/.venv \
    PATH="/dependencies/.venv/bin:$PATH" \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=America/Santiago

# Build tools + headers to compile psycopg2, asyncpg, and pydantic-core.
RUN apk add --no-cache \
    bash \
    gcc \
    g++ \
    libc-dev \
    libffi-dev \
    make \
    tzdata \
    linux-headers \
    musl-dev \
    openssl-dev \
    libexpat \
    postgresql-dev \
    && pip install --no-cache-dir pip==25.1.1 poetry==1.8.5 setuptools==78.1.1 wheel==0.46.2

WORKDIR /dependencies

COPY pyproject.toml poetry.lock ./

# -----------------------------------------------------------------------------
# final-builder: installs production dependencies into the virtualenv.
# Excludes test and lint groups to keep the prod venv lean.
# -----------------------------------------------------------------------------
FROM base AS final-builder

RUN poetry install --without test,lint --no-root --no-cache

WORKDIR /code

# -----------------------------------------------------------------------------
# tests-builder: installs production + test dependencies into the virtualenv.
# Includes pytest and httpx; excludes the lint group.
# -----------------------------------------------------------------------------
FROM base AS tests-builder

RUN poetry install --with test --no-root --no-cache

WORKDIR /code

# -----------------------------------------------------------------------------
# base-small: clean runtime base shared by final and tests.
# Fresh Alpine image with only the runtime libraries required to load compiled
# C extensions. No compiler, no build headers, no poetry.
# Creates a non-root user (app) for all executable stages.
# -----------------------------------------------------------------------------
FROM --platform=$TARGETPLATFORM python:3.13-alpine3.21 AS base-small

ENV VIRTUAL_ENV=/dependencies/.venv \
    PATH="/dependencies/.venv/bin:$PATH" \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=America/Santiago

# Runtime libs: libffi and libexpat for compiled extensions, libpq for psycopg2.
RUN apk add --no-cache \
    bash \
    tzdata \
    libexpat \
    libffi \
    libpq \
    && adduser -D -g '' app

WORKDIR /code

# -----------------------------------------------------------------------------
# final: production image.
# Copies the pre-built prod venv from final-builder and runs as non-root.
# -----------------------------------------------------------------------------
FROM base-small AS final

COPY --from=final-builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY src/ ./src/

ENV PYTHONPATH=/code

RUN chown -R app:app ./src

USER app

CMD ["sh", "-c", "uvicorn src.presentation.api.main:api --host 0.0.0.0 --port ${PORT:-8080}"]

# -----------------------------------------------------------------------------
# tests: CI/testing image.
# Copies the pre-built test venv from tests-builder and runs as non-root.
# -----------------------------------------------------------------------------
FROM base-small AS tests

COPY --from=tests-builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY . .

ENV PYTHONPATH=/code

RUN chown -R app:app .

USER app
