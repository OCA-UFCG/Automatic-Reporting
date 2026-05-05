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
import html
import os
from dotenv import load_dotenv
import re
from datetime import datetime
from weasyprint import HTML
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from plotting import gerar_grafico_sexo
from plotting import gerar_grafico_populacao_etaria_sexo
from plotting import gerar_grafico_serie_temporal_mortalidade_infantil
from plotting import gerar_grafico_estabelecimento_saude

CHART_TYPES = {
    "grafico_sexo": gerar_grafico_sexo,
    "grafico_populacao_etaria_sexo":gerar_grafico_populacao_etaria_sexo,
    "grafico_mortalidade_infantil":gerar_grafico_serie_temporal_mortalidade_infantil,
    "grafico_estabelecimento_saude":gerar_grafico_estabelecimento_saude
}

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

carregado = load_dotenv(dotenv_path='.env')
DEMOGRAFIA_CSV_URL = os.getenv("DEMOGRAFIA_CSV_URL")
DEFAULT_DOCS_URL = os.getenv("DEFAULT_DOCS_URL")
DEMOGRAFIA_FAKE_CSV = "demografia-fake.csv"
SAUDE_CSV = "saude-fake.csv"
SAUDE_ESTABELECIMENTO_CSV = "saude-estabelecimento.csv"

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
            texto = response.read().decode("utf-8")
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

    linhas = texto.splitlines()
    linhas_filtradas = [linha for linha in linhas if not re.search(r'\[\w+\]', linha)]
    return '\n'.join(linhas_filtradas)


def texto_para_html(texto: str, contexto: dict, graficos: dict[str, str] = {}) -> str:
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
    texto_normalizado = re.sub(
        r"\$([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)",
        substituir_placeholder_dolar,
        texto_normalizado,
    )
    for alias, valor in alias_map.items():
        texto_normalizado = texto_normalizado.replace(f"${alias}", str(valor))

    texto_renderizado = Template(texto_normalizado).render(**contexto)

    # Substitui %%marcadores%% por blocos <figure> ANTES do escape
    def substituir_grafico(match: re.Match) -> str:
        conteudo = match.group(1).lower()
        tipos = [t.strip() for t in conteudo.split("+")]

        figuras = []
        for tipo in tipos:
            arquivo = graficos.get(tipo)
            if arquivo:
                figuras.append(
                    f'<figure style="flex:1; text-align:center; margin:0;">'
                    f'<img src="/output/{arquivo}" alt="Gráfico {tipo}" style="width:100%; height:auto;">'
                    f'<figcaption>Figura – {tipo.capitalize()}</figcaption>'
                    f'</figure>'
                )

        if not figuras:
            return ""

        wrapper = (
            f'<div style="display:flex; gap:16px; align-items:flex-start; margin:24px 0;">'
            + "".join(figuras)
            + '</div>'
        )
        return f'\x00GRAFICO\x00{wrapper}\x00FIMGRAFICO\x00'

    texto_marcado = re.sub(r"%%(\w+(?:\+\w+)*)", substituir_grafico, texto_renderizado)

    linhas = [linha.rstrip() for linha in texto_marcado.splitlines()]
    html_lines = []
    em_lista = False

    for linha in linhas:
        linha_limpa = linha.lstrip("\ufeff").strip()
        if not linha_limpa:
            if em_lista:
                html_lines.append("</ul>")
                em_lista = False
            continue

        # Linha de gráfico: já é HTML puro, não passa pelo escape
        if "\x00GRAFICO\x00" in linha_limpa:
            if em_lista:
                html_lines.append("</ul>")
                em_lista = False
            conteudo = linha_limpa.replace("\x00GRAFICO\x00", "").replace("\x00FIMGRAFICO\x00", "")
            html_lines.append(conteudo)
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
    # 1. Exact match (case-insensitive)
    mascara_exata = serie_cidades.str.lower() == cidade_informada.lower()
    if mascara_exata.any():
        return df[mascara_exata]
    # 2. Fallback: strip state abbreviations like "(PB)" and match
    cidade_sem_uf = normalizar_nome_cidade(cidade_informada)
    serie_sem_uf = serie_cidades.str.replace(r"\s*\([A-Za-z]{2}\)\s*$", "", regex=True)
    mascara_sem_uf = serie_sem_uf.str.lower() == cidade_sem_uf.lower()
    matched = df[mascara_sem_uf]
    if matched.empty:
        return matched
    # 3. Check for ambiguity: multiple states matched
    states = serie_cidades[mascara_sem_uf].str.extract(r"\(([A-Za-z]{2})\)$")[0].dropna().unique()
    if len(states) > 1:
        raise ValueError(
            f"Cidade ambígua: '{cidade_informada}' encontrada em {', '.join(sorted(states))}. "
            f"Indique o estado, ex: '{cidade_sem_uf} ({states[0]})'"
        )
    return matched


@app.get("/cities")
async def listar_cidades():
    return carregar_cidades()

@app.get("/relatorios")
async def listar_relatorios():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    relatorios = []

    for pdf_file in OUTPUT_DIR.glob("relatorio_*.pdf"):
        nome_base = pdf_file.stem
        html_file = OUTPUT_DIR / f"{nome_base}.html"

        stat = pdf_file.stat()
        criado_em = datetime.fromtimestamp(stat.st_mtime)

        slug_completo = nome_base.replace("relatorio_", "", 1)
        if "__" in slug_completo:
            slug_cidade, _timestamp = slug_completo.rsplit("__", 1)
        else:
            slug_cidade = slug_completo

        cidade = re.sub(r"_+", " ", slug_cidade).strip().title()

        relatorios.append({
            "cidade": cidade,
            "arquivo_pdf": pdf_file.name,
            "arquivo_html": html_file.name if html_file.exists() else None,
            "data": criado_em.strftime("%d/%m/%Y"),
            "hora": criado_em.strftime("%H:%M:%S"),
            "pdf_url": f"/output/{pdf_file.name}",
            "html_url": f"/output/{html_file.name}" if html_file.exists() else None,
        })

    relatorios.sort(
        key=lambda item: datetime.strptime(
            f"{item['data']} {item['hora']}", "%d/%m/%Y %H:%M:%S"
        ),
        reverse=True
    )

    return relatorios


@app.delete("/relatorios/{arquivo_pdf}")
async def apagar_relatorio(arquivo_pdf: str):
    nome_arquivo = arquivo_pdf.strip()

    if "/" in nome_arquivo or "\\" in nome_arquivo:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido.")

    if not nome_arquivo.startswith("relatorio_") or not nome_arquivo.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Arquivo de relatório inválido.")

    pdf_path = OUTPUT_DIR / nome_arquivo
    nome_base = pdf_path.stem
    html_path = OUTPUT_DIR / f"{nome_base}.html"

    sufixo_relatorio = nome_base.replace("relatorio_", "", 1)
    chart_path = OUTPUT_DIR / f"grafico_sexo_{sufixo_relatorio}.png"

    removidos = []
    for caminho in [pdf_path, html_path, chart_path]:
        if caminho.exists() and caminho.is_file():
            caminho.unlink()
            removidos.append(caminho.name)

    if not removidos:
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")

    return {"ok": True, "removidos": removidos}

@app.get("/relatorio/{cidade}", response_class=HTMLResponse)
async def gerar_relatorio(cidade: str, charts: str = "all"):
    df_demografia = pd.read_csv(DEMOGRAFIA_CSV_URL, delimiter=";", thousands=".")
    df_demografia_fake = pd.read_csv(DEMOGRAFIA_FAKE_CSV, delimiter=",", thousands=".")
    df_saude = pd.read_csv(SAUDE_CSV, delimiter=",")
    df_saude_estabelecimento = pd.read_csv(SAUDE_ESTABELECIMENTO_CSV, delimiter=",")
    
    try:
        linhas_df_demografia = filtrar_linhas_por_cidade(df_demografia, cidade)
        linhas_df_demografia_fake = filtrar_linhas_por_cidade(df_demografia_fake, cidade)
        linhas_df_saude = filtrar_linhas_por_cidade(df_saude, cidade)
        linhas_df_saude_estabelecimento = filtrar_linhas_por_cidade(df_saude_estabelecimento, cidade)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

    linhas_demografia = linhas_df_demografia.to_dict("records")
    linhas_demografia_fake = linhas_df_demografia_fake.to_dict("records")
    linhas_saude = linhas_df_saude.to_dict("records")
    linhas_saude_estabelecimento = linhas_df_saude_estabelecimento.to_dict("records")

    if not linhas_demografia:
        raise HTTPException(status_code=404, detail=f"Cidade '{cidade}' não encontrada.")

    safe_city = re.sub(r"[^a-zA-Z0-9_-]+", "_", linhas_demografia[0]["nm_mun"].strip().lower())

    # resolve quais tipos de gráfico gerar
    allowed = set(CHART_TYPES.keys())
    if charts == "all":
        to_generate = list(CHART_TYPES.keys())
    else:
        requested = [c.strip() for c in charts.split(",")]
        invalid = set(requested) - allowed
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo(s) de gráfico inválido(s): {invalid}. Tipos válidos: {', '.join(allowed)}"
            )
        to_generate = requested

    # gera os gráficos como dict ANTES do HTML
    graficos: dict[str, str] = {}
    for chart_type in to_generate:
        chart_func = CHART_TYPES[chart_type]
        if chart_type == "grafico_sexo":
            graficos[chart_type] = chart_func(linhas_demografia[0], OUTPUT_DIR, safe_city)
        elif chart_type == "grafico_populacao_etaria_sexo":
            graficos[chart_type] = chart_func(linhas_demografia_fake[0], OUTPUT_DIR, safe_city)
        elif chart_type == "grafico_mortalidade_infantil":
            graficos[chart_type] = chart_func(linhas_saude[0], OUTPUT_DIR, safe_city)
        elif chart_type == "grafico_estabelecimento_saude":
            graficos[chart_type] = chart_func(linhas_saude_estabelecimento[0], OUTPUT_DIR, safe_city)

    # If DATANE_DOCS_URL is set but empty (common in docker-compose), fall back to default.
    docs_url = os.getenv("DATANE_DOCS_URL") or DEFAULT_DOCS_URL
    try:
        docs_texto = carregar_texto_do_docs(docs_url)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    # converte texto → HTML já com os gráficos embutidos
    docs_html = texto_para_html(docs_texto, linhas_demografia[0], graficos)

    # renderiza o template
    template = Template(TEMPLATE_STRING)
    html_out = template.render(dados=linhas_demografia, docs_html=docs_html)

    # Output file handling
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"relatorio_{safe_city}.html"
    output_file.write_text(html_out, encoding="utf-8")

    # Gerar PDF usando WeasyPrint
    pdf_file = OUTPUT_DIR / f"relatorio_{safe_city}.pdf"
    HTML(string=html_out, base_url=str(OUTPUT_DIR.resolve())).write_pdf(str(pdf_file))

    return HTMLResponse(content=html_out)

# If the frontend has been built (e.g., via Docker), serve it from the same app.
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"
if FRONTEND_DIST_DIR.exists():
    @app.get("/")
    async def frontend_index():
        return FileResponse(FRONTEND_DIST_DIR / "index.html")

    # Vite outputs assets under dist/assets; mounting the whole dist keeps it simple.
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST_DIR), html=True), name="frontend")