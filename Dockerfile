### Build frontend (Vite)
FROM node:18-alpine AS frontend-build

WORKDIR /app/frontend

# ARG VITE_API_BASE_URL

# ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN corepack enable

COPY frontend/package.json frontend/yarn.lock ./
RUN yarn install --frozen-lockfile

COPY frontend/ ./

# Build static assets
RUN yarn build


### Runtime (FastAPI + built frontend)
FROM python:3.11-slim AS runtime

ARG DEMOGRAFIA_CSV_URL
ARG EDUCACAO_CSV_URL
ARG SAUDE_CSV_URL
ARG ECONOMIA_RENDA_CSV_URL
ARG SANEAMENTO_CSV_URL
ARG HIDRAULICA_CSV_URL
ARG DEMOGRAFIA_DOCS_URL
ARG EDUCACAO_DOCS_URL
ARG SAUDE_DOCS_URL
ARG ECONOMIA_RENDA_DOCS_URL
ARG SANEAMENTO_DOCS_URL
ARG HIDRAULICA_DOCS_URL
ARG MAP_SHAPE_ZIP_URL
ARG MAP_SHAPE_ASSET_NAME

ENV DEMOGRAFIA_CSV_URL=$DEMOGRAFIA_CSV_URL
ENV EDUCACAO_CSV_URL=$EDUCACAO_CSV_URL
ENV SAUDE_CSV_URL=$SAUDE_CSV_URL
ENV ECONOMIA_RENDA_CSV_URL=$ECONOMIA_RENDA_CSV_URL
ENV SANEAMENTO_CSV_URL=$SANEAMENTO_CSV_URL
ENV HIDRAULICA_CSV_URL=$HIDRAULICA_CSV_URL
ENV DEMOGRAFIA_DOCS_URL=$DEMOGRAFIA_DOCS_URL
ENV EDUCACAO_DOCS_URL=$EDUCACAO_DOCS_URL
ENV SAUDE_DOCS_URL=$SAUDE_DOCS_URL
ENV ECONOMIA_RENDA_DOCS_URL=$ECONOMIA_RENDA_DOCS_URL
ENV SANEAMENTO_DOCS_URL=$SANEAMENTO_DOCS_URL
ENV HIDRAULICA_DOCS_URL=$HIDRAULICA_DOCS_URL
ENV MAP_SHAPE_ZIP_URL=$MAP_SHAPE_ZIP_URL
ENV MAP_SHAPE_ASSET_NAME=$MAP_SHAPE_ASSET_NAME
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

RUN if [ -n "$MAP_SHAPE_ZIP_URL" ]; then python scripts/download_map_shapes.py; fi

# Copy built frontend into expected location
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

EXPOSE 8000

# Uvicorn is pulled in via requirements.txt
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
