# Automatic Reporting

Sistema de geração de relatórios PDF para o Data Nordeste. Combina dados de CSVs com textos descritivos do Google Docs e renderiza relatórios visuais em PDF.

## Arquitetura

```
Browser (React SPA)
       │
       ▼
FastAPI (Python) ──────► Node.js (React SSR)
       │                       │
       │                       ▼
       │                  HTML renderizado
       ▼                       │
WeasyPrint                     │
       │                       │
       ▼                       │
     PDF ◄─────────────────────┘
```

- **Python/FastAPI**: processa dados, gerencia CSV, Docs, gráficos
- **React SSR**: renderiza HTML da capa e conteúdo via `renderToStaticMarkup`
- **WeasyPrint**: converte HTML em PDF

## Stack

- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: React + Vite
- **PDF**: WeasyPrint + React SSR
- **Build**: npm workspaces (monorepo)

## Requisitos

- Python 3.11+
- Node.js 18+
- npm

## Quick start

```bash
# Ativar ambiente virtual e rodar
source .venv/bin/activate && ./build.sh
```

Isso instala dependências Python e JS, builda o SSR e o frontend, e sobe os servidores.

## Componentes do build

```bash
pip install -r requirements.txt    # Python deps
npm install                          # Node deps
npm run build -w report              # Build React SSR → report/ssr-dist/
npm run build -w frontend            # Build SPA → frontend/dist/
```

## Como rodar

```bash
source .venv/bin/activate && ./build.sh
```

O `build.sh` inicia:
- Servidor SSR (Node.js) na porta 3001
- API FastAPI na porta 8000

## Endpoints da API

| Método | URL | Descrição |
|--------|-----|-----------|
| GET | `/cities` | Lista de cidades |
| GET | `/macrotemas` | Lista de macrotemas |
| GET | `/relatorios` | Relatórios gerados |
| GET | `/relatorio/{cidade}?macrotema={tema}` | Gera relatório |
| DELETE | `/relatorios/{arquivo}` | Remove relatório |

## Macrotemas

- `todos` — Todos os temas concatenados
- `demografia` — Demografia
- `educacao` — Educação
- `saude` — Saúde
- `economia-renda` — Economia e Renda
- `saneamento` — Saneamento
- `hidraulica` — Segurança Hídrica

## Estrutura de diretórios

```
/
├── main.py                # FastAPI app
├── reports.py             # Lógica de geração (orquestrador)
├── config.py              # Configurações e variáveis de ambiente
├── plotting.py             # Gráficos matplotlib
│
├── frontend/              # SPA React (interface)
│   └── src/App.jsx
│
├── report/                # React SSR (renderização PDF)
│   └── src/components/    # Cover, Report, Brand, etc.
│
├── utils/
│   ├── cover.py           # Monta objeto "cover" para o React
│   ├── renderer.py        # Converte markdown Docs → HTML
│   ├── ssr.py             # Chama Node.js para renderizar
│   ├── docs.py            # Baixa Google Docs
│   ├── cities.py          # Filtro e список cidades
│   ├── macrotemas.py      # Config dos temas
│   └── maps.py            # Mapas (Contentful ou gerado)
│
├── docs/
│   └── ARCHITECTURE.md    # Documentação da arquitetura
│
└── output/                # Relatórios gerados (.html + .pdf)
```


### Resumo das etapas

| Etapa | O que acontece |
|-------|----------------|
| 1 | Carrega CSV do tema selecionado (pandas) |
| 2 | Filtra linhas pela cidade informada |
| 3 | Gera gráficos matplotlib (só se demografia) |
| 4 | Busca texto no Google Docs (com cache) |
| 5 | Extrai seções marcadas (##resumo_tema, etc.) |
| 6 | Preenche cover com métricas, score, indicadores |
| 7 | Converte markdown dos Docs em HTML |
| 8 | React SSR renderiza HTML final |
| 9 | Salva HTML, PDF gerado em background |


## Variáveis de ambiente

```bash
# URLs dos CSVs (por tema)
DEMOGRAFIA_CSV_URL, EDUCACAO_CSV_URL, SAUDE_CSV_URL, etc.

# URLs dos Docs (por tema)
DEMOGRAFIA_DOCS_URL, EDUCACAO_DOCS_URL, etc.

# Contentful (mapas)
CONTENTFUL_SPACE_ID, CONTENTFUL_ACCESS_TOKEN
```

## Docker

```bash
docker build -t automatic-reporting .
docker run -p 8000:8000 automatic-reporting
```