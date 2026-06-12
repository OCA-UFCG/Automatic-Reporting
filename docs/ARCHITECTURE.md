# Arquitetura do Automatic Reporting

## Visão geral

Geração de relatórios em PDF com dados de CSV + texto do Google Docs. O fluxo é:

```
Browser (SPA) → FastAPI (Python) → subprocess Node (React SSR) → HTML → WeasyPrint → PDF
```

Cada camada tem uma responsabilidade única: Python processa dados, React renderiza apresentação, WeasyPrint converte pra PDF.

---

## Fluxo de execução

### Visão geral em 5 passos

```
┌──────────────────┐     GET /relatorio/{cidade}?macrotema={tema}     ┌─────────────────────┐
│   Browser (SPA)  │ ───────────────────────────────────────────────▶  │   FastAPI :8000     │
│   frontend/src/   │                                               │   reports.py        │
└──────────────────┘                                               └──────────┬──────────┘
         ▲                                                                    │
         │ HTMLResponse                                                        ▼
         │                                                            ┌─────────────────────┐
         │                                                            │  1. Carrega CSV     │
         │                                                            │  2. Filtra cidade   │
         │                                                            │  3. Carrega Docs    │
         │                                                            │  4. Gera gráficos   │
         │                                                            │  5. Prepara cover   │
         │                                                            │  6. Converte Docs→  │
         │                                                            │     HTML            │
         │                                                            └──────────┬──────────┘
         │                                                                       │
         │                                                                       ▼
         │                                                            ┌─────────────────────┐
         │                                                            │  React SSR (Node)   │
         │                                                            │  render_react_ssr() │
         │                                                            │  renderiza cover +  │
         │                                                            │  docsHtml em HTML   │
         │                                                            └──────────┬──────────┘
         │                                                                       │
         │                                                                       ▼
         │                                                            ┌─────────────────────┐
         │                                                            │  WeasyPrint         │
         │                                                            │  HTML → PDF         │
         │                                                            └─────────────────────┘
         │
         │ HTML (one-shot, após PDF em background)
         ◀───────────────────────────────────────────────────────────
```

---

### Fluxo detalhado por etapas

#### 1. Usuário abre formulário no browser (App.jsx)

```jsx
// frontend/src/App.jsx
const url = `${API_BASE}/relatorio/${encodeURIComponent(cidade)}?macrotema=${macrotema}`;
window.open(url, "_blank");
```

O browser abre uma nova aba com a URL: `GET /relatorio/{cidade}?macrotema={tema}`

#### 2. FastAPI recebe a requisição (main.py)

```python
@app.get("/relatorio/{cidade}", response_class=HTMLResponse)
async def gerar_relatorio(cidade: str, macrotema: str = "demografia", ...):
    return await gerar_relatorio_handler(cidade, macrotema, charts, background_tasks=background_tasks)
```

#### 3. `gerar_relatorio_handler` processa dados (reports.py)

O handler executa em loop para cada macrotema solicitado:

**3.1 Para cada macrotema — carrega CSV:**
```python
df = pd.read_csv(csv_source, delimiter=";")
df = normalizar_colunas_macrotema(df, macrotema_slug)
linhas_df = filtrar_linhas_por_cidade(df, cidade)  # utils/cities.py
linhas_macrotema = linhas_df.to_dict("records")
```

**3.2 Na primeira iteração — gera cover:**
```python
cover = montar_capa_relatorio(linhas[0], gerado_em, macrotema_dados["nome"])
# utils/cover.py — retorna dicionário com métricas, score, macrotema, indicadores
```

**3.3 Se demografia — gera gráficos:**
```python
chart_file = gerar_grafico_sexo(linhas_macrotema[0], OUTPUT_DIR, safe_report)
chart_file = gerar_grafico_porte(df, OUTPUT_DIR, safe_report)
chart_file = gerar_grafico_top_cidades(df, OUTPUT_DIR)
# plotting.py — matplotlib
```

**3.4 Carrega texto dos Docs:**
```python
docs_texto = carregar_texto_do_docs(docs_url)  # utils/docs.py
# Busca texto do Google Docs e faz cache local
```

**3.5 Extrai seções do documento:**
```python
resumo_tema, docs_texto = extrair_resumo_tema(docs_texto)
resumo_relatorio, docs_texto = extrair_resumo_relatorio(docs_texto)
resumo_cidade, docs_texto = extrair_resumo_cidade(docs_texto)
descricao_tema, docs_texto = extrair_descricao_tema(docs_texto)
# Extrai blocos marcados no Docs (ex: ##resumo_tema, ##descricao_tema)
```

**3.6 Preenche cover (só na primeira iteração):**
```python
cover["macrotema"]["resumo"] = substituir_placeholders(resumo_tema, ...)
cover["macrotema"]["descricao"] = substituir_placeholders(descricao_tema, ...)
```

**3.7 Detecta mapa:**
```python
if "*mapa_geografico" in docs_texto:
    mapa_principal = render_mapa_marker(linhas_macrotema[0], safe_report)
# utils/renderer.py — tenta Contentful ou gera mapa local
```

**3.8 Converte texto Docs em HTML:**
```python
docs_html_parts.append(
    texto_para_html(docs_texto_sem_mapa, linhas_macrotema[0], namespace=macrotema_slug)
)
# utils/renderer.py — processa marcadores (%%grafico, ##componente, $placeholders)
```

#### 4. Chama React SSR (reports.py → ssr.py → Node)

```python
html_content = await render_react_ssr({
    "cover": cover,
    "docsHtml": docs_html,  # HTML de todos os macrotemas concatenados
    "dados": linhas,
})
```

O Python inicia um **subprocess Node.js** que executa React no servidor:

```
reports.py                          ssr.py                          Node.js
    │                                  │                               │
    │  render_react_ssr(props) ───────▶│                               │
    │                                  │  subprocess.run(["node",     │
    │                                  │    "entry.js", JSON]) ──────▶│
    │                                  │                               │ React.createElement()
    │                                  │                               │ renderToStaticMarkup()
    │                                  │◀──── HTML via stdout ────────│
    │◀─── HTML string ─────────────────│                               │
```

O React **não chama Python** — é puramente renderização one-shot. Node.js recebe JSON via argumento, renderiza, e devolve HTML via stdout.

#### 5. Salva HTML e agenda PDF (reports.py)

```python
output_file = OUTPUT_DIR / f"relatorio_{safe_report}.html"
output_file.write_text(html_content, encoding="utf-8")

pdf_file = OUTPUT_DIR / f"relatorio_{safe_report}.pdf"
background_tasks.add_task(_gerar_pdf, html_content, pdf_file)
```

O PDF é gerado em background via **WeasyPrint** (não é blocking).

#### 6. Browser recebe HTML e mostra relatório

O browser recebe o HTML já renderizado (cover + conteúdo). O PDF é gerado em paralelo.

---

## Estrutura de diretórios

```
/
├── main.py                     # FastAPI app, rotas /cities, /relatorios, /relatorio/{cidade}
├── config.py                   # Config (OUTPUT_DIR, variáveis de ambiente)
├── reports.py                  # Lógica de geração de relatório (orquestrador)
├── plotting.py                 # Gráficos matplotlib (sexo, porte, top cidades)
├── requirements.txt            # Dependências Python
├── Dockerfile                  # Build em 3 estágios
│
├── frontend/                   # SPA React (interface do usuário)
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx            # Entry point
│       ├── App.jsx             # Componente principal (formulário + lista)
│       └── styles.css          # Estilos da interface
│
├── report/                     # React SSR (geração de PDF)
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── ssr-entry.jsx       # Entry point SSR (lê JSON, chama renderToStaticMarkup)
│       ├── ssr-server.jsx      # Servidor HTTP persistente para SSR
│       ├── styles.js           # CSS do relatório PDF
│       └── components/
│           ├── Report.jsx      # Componente raiz
│           ├── Cover.jsx       # Capa
│           ├── Brand.jsx       # SVGs e ícones
│           ├── ThemeDetail.jsx # Detalhamento do tema
│           └── PdfLayout.jsx   # Header/footer do PDF
│
├── utils/
│   ├── cover.py                # Monta objeto "cover" pros componentes
│   ├── renderer.py              # Converte markdown dos Docs → HTML
│   ├── ssr.py                  # Chama Node.js SSR via subprocess
│   ├── docs.py                 # Baixa e processa Google Docs
│   ├── cities.py               # Filtro por cidade
│   ├── macrotemas.py           # Config dos temas (URLs de CSV/Docs)
│   └── maps.py                 # Mapas (Contentful ou gerado localmente)
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
        "mapa_principal": str,        # HTML do <figure> com mapa
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
            "descricao_paragrafos": [str],
            "descricao_html": [str],
            "indicadores": [
                {"nome": str, "fonte": str, "score": str, "classe": str, "icone": str}
            ]
        },
        "resumo_relatorio": str,
        "resumo_relatorio_html": [str],
        "resumo_cidade": str,
        "resumo_cidade_html": [str],
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
4. `runtime` — Python + Node.js + WeasyPrint

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
| **Build extra** | Precisa rodar `npm run build -w report` |
| **Curva** | Jinja é só HTML + tags; React JSX exige conhecimento do ecossistema |
| **Dois runtimes** | Python + Node.js rodando lado a lado (mais processos que antes só Python) |

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

> Documento gerado em 27/05/2026. Atualizado em 12/06/2026.