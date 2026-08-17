### Stage 1: Install all JS dependencies (monorepo workspaces)
FROM node:18-alpine AS deps

WORKDIR /app

COPY package.json ./
COPY frontend/package.json ./frontend/
COPY report/package.json ./report/

RUN npm install


### Stage 2: Build frontend SPA
FROM deps AS frontend-build

COPY frontend/ ./frontend/
RUN npm run build -w frontend


### Stage 3: Build SSR bundle
FROM deps AS ssr-build

COPY report/ ./report/
RUN npm run build -w report


### Stage 4: Runtime (FastAPI + Node SSR server)
FROM node:18-slim AS runtime

ARG DEMOGRAFIA_CSV_URL
ARG EDUCACAO_CSV_URL
ARG SAUDE_CSV_URL
ARG ECONOMIA_RENDA_CSV_URL
ARG SANEAMENTO_CSV_URL
ARG HIDRAULICA_CSV_URL
ARG CARACTERISTICAS_DOCS_URL
ARG DEMOGRAFIA_DOCS_URL
ARG EDUCACAO_DOCS_URL
ARG SAUDE_DOCS_URL
ARG ECONOMIA_RENDA_DOCS_URL
ARG SANEAMENTO_DOCS_URL
ARG HIDRAULICA_DOCS_URL
ARG DESENVOLVIMENTO_SOCIAL_DOCS_URL
ARG MEIO_AMBIENTE_DOCS_URL

ENV DEMOGRAFIA_CSV_URL=$DEMOGRAFIA_CSV_URL
ENV EDUCACAO_CSV_URL=$EDUCACAO_CSV_URL
ENV SAUDE_CSV_URL=$SAUDE_CSV_URL
ENV ECONOMIA_RENDA_CSV_URL=$ECONOMIA_RENDA_CSV_URL
ENV SANEAMENTO_CSV_URL=$SANEAMENTO_CSV_URL
ENV HIDRAULICA_CSV_URL=$HIDRAULICA_CSV_URL
ENV CARACTERISTICAS_DOCS_URL=$CARACTERISTICAS_DOCS_URL
ENV DEMOGRAFIA_DOCS_URL=$DEMOGRAFIA_DOCS_URL
ENV EDUCACAO_DOCS_URL=$EDUCACAO_DOCS_URL
ENV SAUDE_DOCS_URL=$SAUDE_DOCS_URL
ENV ECONOMIA_RENDA_DOCS_URL=$ECONOMIA_RENDA_DOCS_URL
ENV SANEAMENTO_DOCS_URL=$SANEAMENTO_DOCS_URL
ENV HIDRAULICA_DOCS_URL=$HIDRAULICA_DOCS_URL
ENV DESENVOLVIMENTO_SOCIAL_DOCS_URL=$DESENVOLVIMENTO_SOCIAL_DOCS_URL
ENV MEIO_AMBIENTE_DOCS_URL=$MEIO_AMBIENTE_DOCS_URL

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# System deps for weasyprint + matplotlib
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
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

RUN python3 -m venv /opt/venv \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy all source code
COPY . ./

# Copy built assets from previous stages
COPY --from=deps /app/node_modules ./node_modules
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
COPY --from=ssr-build /app/report/ssr-dist ./report/ssr-dist

EXPOSE 8000

# Start both SSR server and FastAPI
CMD ["sh", "-c", "node report/ssr-dist/server.js & python3 -m uvicorn main:app --host 0.0.0.0 --port 8000"]
