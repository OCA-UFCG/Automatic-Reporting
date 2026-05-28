# Arquitetura do Automatic Reporting

## Visão geral

Geração de relatórios em PDF com dados de CSV + texto do Google Docs. O fluxo é:

```
Browser (SPA) → FastAPI (Python) → subprocess Node (React SSR) → HTML → WeasyPrint → PDF
```

Cada camada tem uma responsabilidade única: Python processa dados, React renderiza apresentação, WeasyPrint converte pra PDF.

---

## Fluxo detalhado

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Browser (React SPA)                          │
│  frontend/src/App.jsx                                               │
│  Interface pra selecionar cidade + macrotema                        │
│  Comunica com FastAPI via fetch()                                   │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ GET /relatorio/{cidade}?macrotema={tema}
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                FastAPI (Python) — main.py :8000                      │
│                                                                      │
│  reports.py — gerar_relatorio_handler():                             │
│                                                                      │
│  1. Lê CSV do Google Drive (pandas)                                  │
│     └── utils/macrotemas.py — URLs de cada tema (demografia,        │
│                                educação, saúde, etc.)                │
│                                                                      │
│  2. Filtra por cidade                                                │
│     └── utils/cities.py — filtrar_linhas_por_cidade()               │
│                                                                      │
│  3. Lê texto descritivo do Google Docs                               │
│     └── utils/docs.py — carregar_texto_do_docs()                    │
│     └── extrai resumo_tema / descricao_tema via marcadores          │
│                                                                      │
│  4. Gera gráficos matplotlib                                         │
│     └── plotting.py — gerar_grafico_sexo(), _porte(), _top_cidades()│
│                                                                      │
│  5. Monta objeto "cover" (dicionário Python)                         │
│     └── utils/cover.py — montar_capa_relatorio()                    │
│     ├── metricas (4 cards: área, população, IDH, PIB)              │
│     ├── score (valor, max, status, descricao)                      │
│     ├── macrotema (nome, icone, status, resumo, indicadores)       │
│     └── data_extenso, cidade_nome, uf                              │
│                                                                      │
│  6. Converte texto markdown dos Docs → HTML                          │
│     └── utils/renderer.py — texto_para_html()                       │
│     ├── processa %%chart, ##componente, $placeholders              │
│     ├── gera <p>, <ul>, <h1>, <h2>, figure-caption                 │
│     └── output: string HTML pronta pra injetar no template         │
│                                                                      │
│  7. Chama React SSR (HTTP POST p/ servidor persistente) ─────┐    │
│     └── utils/ssr.py — render_react_ssr(props)               │    │
│                          │ httpx.post("http://127.0.0.1:3001")│    │
│                                                                      │
│  8. WeasyPrint converte HTML → PDF                                  │
│     └── HTML(string=..., base_url=...).write_pdf(...)               │
│                                                                      │
│  9. Salva .html e .pdf em output/                                   │
│  10. Retorna HTMLResponse pro browser                               │
└───────────────────────────────────────────────────┬─────────────────┘
                                                     │
                                                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│               Node.js — React SSR (report/)                         │
│                                                                      │
│  Chamado via: subprocess.run(["node", "ssr-dist/ssr-entry.js",      │
│                               json.dumps(props)])                    │
│                                                                      │
│  src/ssr-entry.jsx:                                                  │
│    1. Lê JSON de process.argv[2]                                    │
│    2. renderToStaticMarkup(<Report cover={} docsHtml={} dados={} />)│
│    3. Escreve HTML em stdout                                        │
│                                                                      │
│  Componentes (src/components/):                                      │
│                                                                      │
│    Report.jsx ─── componente raiz                                   │
│    ├── <html>, <head> (styles), <body>                              │
│    ├── PdfPageHeader (só aparece no @media print)                   │
│    ├── Cover ──────────────────────────────────────────────────┐   │
│    │   ├── cover-header (brand + data)                         │   │
│    │   ├── cover-city (nome da cidade)                         │   │
│    │   ├── MetricCard × 4 (grid de métricas)                   │   │
│    │   ├── RadarChart (SVG fixo)                               │   │
│    │   ├── ScoreCard (valor + status)                          │   │
│    │   ├── ScoreLegend (legenda fixa)                          │   │
│    │   ├── MacrothemeCard (ícone + nome + status)              │   │
│    │   ├── MacrothemeSummary (resumo)                          │   │
│    │   └── IndicatorScoreCard × N (grid de indicadores)        │   │
│    ├── ThemeDetail (se houver descricao_paragrafos)            │   │
│    ├── <div class="doc-content"> (HTML injetado via            │   │
│    │    dangerouslySetInnerHTML)                               │   │
│    └── PdfFooter                                               │   │
│                                                                      │
│  Brand.jsx — SVGs e ícones:                                         │
│    MACROTHEME_ICONS: health, book, people, drop, water + fallback   │
│    INDICATOR_ICONS: hospital, vaccine, birth, shield, book, ...     │
│    MetricIcon, ScoreIcon, CoverBrand, PdfPageHeaderBrand             │
│                                                                      │
│  styles.js — CSS (extraído do TEMPLATE_STRING original)             │
│    Inclui @page, @media print, @media (max-width)                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Estrutura de diretórios

```
/
├── main.py                     # FastAPI app, rotas /cities, /relatorios, /relatorio/{cidade}
├── config.py                   # Config (OUTPUT_DIR, variáveis de ambiente)
├── reports.py                  # Lógica de geração de relatório (orquestrador)
├── plotting.py                 # Gráficos matplotlib (sexo, porte, top cidades)
├── generate_report.py          # CLI tool standalone (gera HTML de CSV)
├── requirements.txt            # Dependências Python
├── Dockerfile                  # Build em 3 estágios
│
├── frontend/                   # SPA React (interface do usuário)
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx            # Entry point
│       ├── App.jsx             # Componente principal (formulário + lista)
│       └── styles.css          # Estilos da interface
│
├── report/                     # React SSR (geração de PDF)
│   ├── package.json
│   ├── vite.config.js
│   ├── src/
│   │   ├── ssr-entry.jsx       # Entry point SSR (lê JSON, chama renderToStaticMarkup)
│   │   ├── styles.js           # CSS do relatório PDF
│   │   └── components/
│   │       ├── Report.jsx      # Componente raiz
│   │       ├── Cover.jsx       # Capa
│   │       ├── Brand.jsx       # SVGs e ícones
│   │       ├── ThemeDetail.jsx # Detalhamento do tema
│   │       └── PdfLayout.jsx   # Header/footer do PDF
│   └── ssr-dist/               # Build output (gitignored)
│
├── utils/
│   ├── cover.py                # Monta objeto "cover" pros componentes
│   ├── renderer.py             # Converte markdown dos Docs → HTML
│   ├── ssr.py                  # Chama Node.js SSR via subprocess
│   ├── docs.py                 # Baixa e processa Google Docs
│   ├── cities.py               # Filtro por cidade
│   ├── macrotemas.py           # Config dos temas (URLs, seções, aliases)
│   ├── tables.py               # Tabela resumo
│   └── maps.py                 # Mapas (placeholder)
│
├── output/                     # Relatórios gerados (.html + .pdf)
└── assets/                     # Recursos estáticos
```

---

## Dicionário de dados (props do React SSR)

O Python monta um dicionário e passa como `props` pro React SSR:

```python
{
    "cover": {
        "data_extenso": str,          # "27 de maio de 2026"
        "cidade_nome": str,           # "Recife"
        "uf": str,                    # "PE" (ou "")
        "metricas": [                 # 4 cards
            {"rotulo": str, "valor": str, "sufixo": str, "fonte": str, "caption": str}
        ],
        "score": {
            "valor": str,             # "3,66"
            "maximo": str,            # "5"
            "status": str,            # "Acima da média nacional"
            "descricao": str,         # texto explicativo
            "texto_apoio": str        # texto de rodapé do score
        },
        "macrotema": {
            "nome": str,              # "Saúde"
            "icone": str,             # "health" | "book" | "people" | "drop" | "water" | "chart"
            "status": str,            # "Muito acima da média nacional"
            "resumo": str,            # texto
            "descricao_paragrafos": [str],  # parágrafos de detalhamento (ou [])
            "indicadores": [
                {"nome": str, "fonte": str, "score": str, "classe": str, "icone": str}
            ]
        }
    },
    "docsHtml": str,              # HTML do Google Docs (processado por texto_para_html)
    "dados": [dict]               # Linhas do CSV (usado pra loop, conteúdo via docsHtml)
}
```

---

## Pipeline de build

```bash
# 1. Instalar todas as dependências (monorepo — React instalado uma vez)
npm install

# 2. Build frontend (SPA do browser)
npm run build -w frontend     # → frontend/dist/

# 3. Build SSR (renderização de PDF)
npm run build -w report       # → report/ssr-dist/

# 4. Python (dependências)
pip install -r requirements.txt

# 5. Rodar
node report/ssr-dist/server.js &   # Servidor SSR persistente (porta 3001)
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Docker

```bash
docker build -t automatic-reporting .
docker run -p 8000:8000 automatic-reporting
```

O Dockerfile tem 4 estágios:
1. `deps` — instala dependências JS (monorepo, uma única `node_modules`)
2. `frontend-build` — compila a SPA React
3. `ssr-build` — compila o bundle SSR (entry + server)
4. `runtime` — Python + Node.js + WeasyPrint (rota o servidor SSR em background)

---

## Prós e contras

### ✅ Prós

| Aspecto | Benefício |
|---|---|
| **Manutenção** | Componentes pequenos (Cover, Brand, ThemeDetail). Mexeu no radar? Só Cover.jsx |
| **Editor** | JSX com syntax highlighting, fechamento automático, validação |
| **Separação** | Python processa dados, React renderiza apresentação |
| **Testabilidade** | Dá pra testar `renderToStaticMarkup(<Cover cover={mock} />)` sem browser |
| **Evolução** | Fácil migrar pra TypeScript, CSS Modules, Tailwind |

### ❌ Contras

| Aspecto | Impacto |
|---|---|
| **Build extra** | Precisa rodar `npm run build -w report` (antes não tinha build step) |
| **Curva** | Jinja é só HTML + tags; React JSX exige conhecimento do ecossistema |
| **Dois runtimes** | Python + Node.js rodando lado a lado (mais processos que antes só Python) |

---

## Sugestões de melhoria

### ~~1. Servidor Node persistente~~ ✅ Implementado
`report/src/ssr-server.jsx` roda um servidor HTTP que mantém o React carregado em memória. Python faz POST em vez de subprocess.

```
Antes:  subprocess.run → ~200ms cada requisição
Depois: HTTP POST → ~5ms cada requisição
```

### ~~2. Monorepo com npm workspaces~~ ✅ Implementado
`package.json` na raiz com `workspaces: ["frontend", "report"]`. React e react-dom instalados uma vez só em `/node_modules`.

```
/
├── package.json         # workspaces: ["frontend", "report"]
├── frontend/
├── report/
└── node_modules/        # único, compartilhado
```

### 3. CSS Modules ou Tailwind
Em vez de uma string CSS gigante em `styles.js`, usar CSS Modules (`Cover.module.css`) ou Tailwind (sem impacto no bundle do cliente, já que é SSR).

### 4. Testes de snapshot nos componentes
```js
import { renderToStaticMarkup } from 'react-dom/server';
import Cover from './Cover';

test('Cover renderiza métricas', () => {
  const html = renderToStaticMarkup(<Cover cover={mockCover} />);
  expect(html).toContain('metric-card');
  expect(html).toContain('Recife');
});
```

---

## Referências

| Arquivo | Função |
|---|---|
| `reports.py` | Orquestrador da geração |
| `utils/cover.py` | Monta o dicionário `cover` |
| `utils/renderer.py` | Converte markdown Docs → HTML |
| `utils/ssr.py` | Chama React SSR via subprocess |
| `utils/docs.py` | Baixa Google Docs |
| `report/src/components/Cover.jsx` | Componente React da capa |
| `report/src/styles.js` | CSS do PDF |

> Documento gerado em 27/05/2026. Mantenha atualizado conforme mudanças na arquitetura.
