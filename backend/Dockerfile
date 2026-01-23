
# backend/Dockerfile
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
  libpq5 libpq-dev gcc \
  && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.backend.txt /app/requirements.txt

# cache de pip (acelera rebuilds) – requer BuildKit
RUN --mount=type=cache,target=/root/.cache/pip \
  pip install --upgrade pip && \
  pip install --default-timeout=300 --retries=10 -r /app/requirements.txt

COPY backend /app/backend
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
