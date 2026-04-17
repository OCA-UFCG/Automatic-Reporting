### Build frontend (Vite)
FROM node:18-alpine AS frontend-build

WORKDIR /app/frontend

# Enable yarn via corepack (Node 18+)
RUN corepack enable

COPY frontend/package.json frontend/yarn.lock ./
RUN yarn install --frozen-lockfile

COPY frontend/ ./

# Build static assets
RUN yarn build


### Runtime (FastAPI + built frontend)
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for weasyprint + matplotlib
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libffi8 \
        shared-mime-info \
        fonts-dejavu-core \
        libfreetype6 \
        libpng16-16 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy API source
COPY . ./

# Copy built frontend into expected location
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

EXPOSE 8000

# Uvicorn is pulled in via requirements.txt
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
