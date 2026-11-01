FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_DEV=1 \
    PATH="/app/backend/.venv/bin:${PATH}"

RUN addgroup --system placementos && adduser --system --ingroup placementos placementos \
    && pip install --no-cache-dir uv==0.13.6

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./backend/
COPY backend/src ./backend/src
COPY backend/migrations ./backend/migrations
COPY backend/alembic.ini ./backend/alembic.ini
RUN uv sync --project backend --frozen --no-dev \
    && chown -R placementos:placementos /app

USER placementos
EXPOSE 8000
CMD ["uvicorn", "placementos.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
