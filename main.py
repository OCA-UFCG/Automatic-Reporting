from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from jinja2 import Template
from pathlib import Path
import ast
from urllib.parse import urlparse
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
import matplotlib.pyplot as plt
import html
import os
import re
from weasyprint import HTML
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from plotting import gerar_grafico_sexo

app = FastAPI()
BASE_DIR = Path(__file__).resolve().parent
app.mount("/output", StaticFiles(directory=str(BASE_DIR / "output")), name="output")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = BASE_DIR / "output"
CITIES_FILE = BASE_DIR / "citys.txt"
DEMOGRAFIA_CSV_URL = "https://raw.githubusercontent.com/OCA-UFCG/Automatic-Reporting/refs/heads/main/report-generator-demo/demografia.csv"
DEFAULT_DOCS_URL = "https://docs.google.com/document/d/1WA3LcQAWIKFYu6MmuF4RSrGFSdYvbpnn/edit?usp=sharing&ouid=102957437660573133451&rtpof=true&sd=true"

FALLBACK_DOC_TEXT = """deu erro.
"""

TEMPLATE_STRING = """
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Data Nordeste – Relatório modelo</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 920px;
            margin: 32px auto;
            padding: 0 24px;
            line-height: 1.65;
            font-size: 16px;
            color: #222;
        }
        h1 {
            font-size: 30px;
            font-weight: 700;
            margin: 0 0 14px 0;
        }
        h2 {
            font-size: 24px;
            font-weight: 700;
            margin: 30px 0 10px 0;
        }
        p {
            margin: 0 0 14px 0;
            text-align: justify;
        }
        .field {
            font-size: 17px;
            margin-bottom: 8px;
        }
        .field strong {
            font-weight: 700;
        }
        .indent {
            text-indent: 1.5em;
        }
        ul {
            margin: 8px 0 16px 28px;
        }
        li {
            margin-bottom: 6px;
        }
        .doc-content p {
            text-indent: 1.5em;
        }
        .doc-content h1 {
            font-size: 34px;
            font-weight: 700;
            margin: 0 0 18px 0;
        }
        .doc-content ul {
            text-indent: 0;
        }
    </style>
</head>
<body>
{% for linha in dados %}

<div class="doc-content">{{ docs_html | safe }}</div>

<h2>Gráfico de população por sexo</h2>
{% set i = 1 %}
<img src="{{ grafico_sexo }}" alt="Gráfico de população por sexo" style="max-width: 100%; height: auto;">
<p> Figura {{ i }} </p>
{% endfor %}
 </body>
</html>
"""


def extrair_doc_id(link_ou_id: str) -> str:
    valor = link_ou_id.strip()
    if "/document/d/" not in valor:
        return valor

    parsed = urlparse(valor)
    partes = [p for p in parsed.path.split("/") if p]
    if "d" in partes:
        idx = partes.index("d")
        if idx + 1 < len(partes):
            return partes[idx + 1]
    raise ValueError("Não foi possível extrair o ID do Google Docs.")


def carregar_texto_do_docs(link_ou_id: str) -> str:
    doc_id = extrair_doc_id(link_ou_id)
    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    try:
        with urlopen(export_url, timeout=20) as response:
            return response.read().decode("utf-8")
    except HTTPError as err:
        if err.code in (401, 403):
            raise ValueError(
                "Google Docs sem acesso público para exportação. "
                "Defina o documento como 'Qualquer pessoa com o link - Leitor' "
                "ou use um documento publicado na web."
            ) from err
        if err.code == 404:
            raise ValueError("Documento do Google Docs não encontrado (404). Verifique o link/ID.") from err
        return FALLBACK_DOC_TEXT
    except (URLError, TimeoutError):
        return FALLBACK_DOC_TEXT


def texto_para_html(texto: str, contexto: dict) -> str:
    def substituir_placeholder_dolar(match: re.Match) -> str:
        namespace = match.group(1).lower()
        campo = match.group(2)
        if namespace in {"demografia", "linha", "dados", "csv"}:
            return str(contexto.get(campo, match.group(0)))
        return match.group(0)

    alias_map = {
        "city": contexto.get("nm_mun", ""),
        "year": contexto.get("ano", ""),
        "municipio": contexto.get("nm_mun", ""),
        "ano": contexto.get("ano", ""),
    }

    texto_normalizado = texto
    texto_normalizado = re.sub(r"\$([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)", substituir_placeholder_dolar, texto_normalizado)
    for alias, valor in alias_map.items():
        texto_normalizado = texto_normalizado.replace(f"${alias}", str(valor))

    texto_renderizado = Template(texto_normalizado).render(**contexto)
    linhas = [linha.rstrip() for linha in texto_renderizado.splitlines()]
    html_lines = []
    em_lista = False

    for linha in linhas:
        linha_limpa = linha.lstrip("\ufeff").strip()
        if not linha_limpa:
            if em_lista:
                html_lines.append("</ul>")
                em_lista = False
            continue

        if linha_limpa.startswith("#!"):
            if em_lista:
                html_lines.append("</ul>")
                em_lista = False
            titulo = linha_limpa[2:].strip()
            if titulo:
                html_lines.append(f"<h1>{html.escape(titulo)}</h1>")
            continue

        if linha_limpa.startswith(("- ", "• ", "* ")):
            if not em_lista:
                html_lines.append("<ul>")
                em_lista = True
            item = html.escape(linha_limpa[2:].strip())
            html_lines.append(f"<li>{item}</li>")
            continue

        if em_lista:
            html_lines.append("</ul>")
            em_lista = False

        if re.match(r"^\d+\.\s+", linha_limpa) or linha_limpa.lower() in {"apresentação", "demografia"}:
            html_lines.append(f"<h2>{html.escape(linha_limpa)}</h2>")
        else:
            html_lines.append(f"<p>{html.escape(linha_limpa)}</p>")

    if em_lista:
        html_lines.append("</ul>")

    return "\n".join(html_lines)




def carregar_cidades() -> list[str]:
    if not CITIES_FILE.exists():
        return []

    conteudo = CITIES_FILE.read_text(encoding="utf-8").strip()
    if not conteudo:
        return []

    try:
        cidades = ast.literal_eval(conteudo)
        if isinstance(cidades, list):
            return [str(cidade).strip() for cidade in cidades if str(cidade).strip()]
    except (ValueError, SyntaxError):
        pass

    return [linha.strip() for linha in conteudo.splitlines() if linha.strip()]


def normalizar_nome_cidade(cidade: str) -> str:
    return re.sub(r"\s*\([A-Za-z]{2}\)\s*$", "", cidade).strip()


def filtrar_linhas_por_cidade(df: pd.DataFrame, cidade: str) -> pd.DataFrame:
    cidade_informada = cidade.strip()
    serie_cidades = df["nm_mun"].astype(str).str.strip()

    mascara_exata = serie_cidades.str.lower() == cidade_informada.lower()
    if mascara_exata.any():
        return df[mascara_exata]

    cidade_sem_uf = normalizar_nome_cidade(cidade_informada)
    serie_sem_uf = serie_cidades.str.replace(r"\s*\([A-Za-z]{2}\)\s*$", "", regex=True)
    mascara_sem_uf = serie_sem_uf.str.lower() == cidade_sem_uf.lower()
    return df[mascara_sem_uf]


@app.get("/cities")
async def listar_cidades():
    return carregar_cidades()

@app.get("/relatorio/{cidade}", response_class=HTMLResponse)
async def gerar_relatorio(cidade: str):
    df = pd.read_csv(DEMOGRAFIA_CSV_URL, delimiter=";")
    linhas_df = filtrar_linhas_por_cidade(df, cidade)
    linhas = linhas_df.to_dict("records")

    if not linhas:
        raise HTTPException(status_code=404, detail=f"Cidade '{cidade}' não encontrada.")

    # If DATANE_DOCS_URL is set but empty (common in docker-compose), fall back to default.
    docs_url = os.getenv("DATANE_DOCS_URL") or DEFAULT_DOCS_URL
    try:
        docs_texto = carregar_texto_do_docs(docs_url)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    docs_html = texto_para_html(docs_texto, linhas[0])

    safe_city = re.sub(r"[^a-zA-Z0-9_-]+", "_", linhas[0]["nm_mun"].strip().lower())
    grafico_sexo = gerar_grafico_sexo(linhas[0], OUTPUT_DIR, safe_city)
    template = Template(TEMPLATE_STRING)
    html = template.render(dados=linhas, grafico_sexo=grafico_sexo, docs_html=docs_html)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"relatorio_{safe_city}.html"
    output_file.write_text(html, encoding="utf-8")
    # Gerar PDF usando WeasyPrint
    pdf_file = OUTPUT_DIR / f"relatorio_{safe_city}.pdf"
    HTML(string=html, base_url=str(OUTPUT_DIR.resolve())).write_pdf(str(pdf_file))

    return HTMLResponse(content=html)


# If the frontend has been built (e.g., via Docker), serve it from the same app.
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"
if FRONTEND_DIST_DIR.exists():
    @app.get("/")
    async def frontend_index():
        return FileResponse(FRONTEND_DIST_DIR / "index.html")

    # Vite outputs assets under dist/assets; mounting the whole dist keeps it simple.
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST_DIR), html=True), name="frontend")
