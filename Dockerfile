### Build frontend (Vite client)
FROM node:18-alpine AS frontend-build

WORKDIR /app/frontend

RUN corepack enable

COPY frontend/package.json frontend/yarn.lock ./
RUN yarn install --frozen-lockfile

COPY frontend/ ./
RUN yarn build


### Build SSR bundle (React report components)
FROM node:18-alpine AS ssr-build

WORKDIR /app/report

COPY report/package.json ./
RUN npm install

COPY report/ ./
RUN npm run build


### Runtime (FastAPI + built frontend + SSR)
FROM node:18-slim AS runtime

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
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for weasyprint + matplotlib
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
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
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy API source
COPY . ./

# Copy built frontend client
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Copy SSR bundle + node_modules
COPY --from=ssr-build /app/report/ssr-dist ./report/ssr-dist
COPY --from=ssr-build /app/report/node_modules ./report/node_modules

EXPOSE 8000

CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
