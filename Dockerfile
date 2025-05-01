# ---------- Stage 1: Builder ----------
# FROM python:3.12.2-slim AS builder

FROM public.ecr.aws/docker/library/python:3.12.2-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ffmpeg build-essential git && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Copy only dependency files first to cache layer
COPY pyproject.toml /app/
COPY poetry.lock /app/

# Install only production dependencies
RUN poetry install --with dev --no-root --no-interaction --no-ansi && \
    rm -rf ~/.cache/pypoetry ~/.cache/pip

# Copy the rest of the application
COPY . /app/


# ---------- Stage 2: Runtime ----------
FROM public.ecr.aws/docker/library/python:3.12.2-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=80

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg && \
    apt-get clean && rm -rf /var/lib/apt/lists/*


    # Create logs directory to support logging
RUN mkdir -p /app/logs


# Copy installed packages and app code from builder stage
COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app

# Set permissions for entrypoints
RUN chmod +x /app/entry.sh /app/entry_celery.sh

EXPOSE ${PORT}
ENTRYPOINT ["/app/entry.sh"]