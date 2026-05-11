from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from jinja2 import Environment
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
from plotting import gerar_grafico_porte
from plotting import gerar_grafico_top_cidades

CHART_TYPES = {
    "sexo": gerar_grafico_sexo,
    "porte": gerar_grafico_porte,
    "top":gerar_grafico_top_cidades,
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

load_dotenv(dotenv_path=BASE_DIR / ".config")
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)


def get_config_value(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


DEMOGRAFIA_CSV_URL = get_config_value("DEMOGRAFIA_CSV_URL")
EDUCACAO_CSV_URL = get_config_value("EDUCACAO_CSV_URL")
SAUDE_CSV_URL = get_config_value("SAUDE_CSV_URL")
ECONOMIA_RENDA_CSV_URL = get_config_value("ECONOMIA_RENDA_CSV_URL")
SANEAMENTO_CSV_URL = get_config_value("SANEAMENTO_CSV_URL")
HIDRAULICA_CSV_URL = get_config_value("HIDRAULICA_CSV_URL")
DEFAULT_DOCS_URL = get_config_value("DEFAULT_DOCS_URL")
DEMOGRAFIA_DOCS_URL = get_config_value("DEMOGRAFIA_DOCS_URL") or DEFAULT_DOCS_URL
EDUCACAO_DOCS_URL = get_config_value("EDUCACAO_DOCS_URL")
SAUDE_DOCS_URL = get_config_value("SAUDE_DOCS_URL")
ECONOMIA_RENDA_DOCS_URL = get_config_value("ECONOMIA_RENDA_DOCS_URL")
SANEAMENTO_DOCS_URL = get_config_value("SANEAMENTO_DOCS_URL")
HIDRAULICA_DOCS_URL = get_config_value("HIDRAULICA_DOCS_URL")

MACROTEMAS = {
    "demografia": {
        "nome": "Demografia",
        "docs_url": DEMOGRAFIA_DOCS_URL,
        "docs_env": "DEMOGRAFIA_DOCS_URL",
        "csv_url": DEMOGRAFIA_CSV_URL,
        "csv_env": "DEMOGRAFIA_CSV_URL",
    },
    "educacao": {
        "nome": "Educação",
        "docs_url": EDUCACAO_DOCS_URL,
        "docs_env": "EDUCACAO_DOCS_URL",
        "csv_url": EDUCACAO_CSV_URL,
        "csv_env": "EDUCACAO_CSV_URL",
    },
    "saude": {
        "nome": "Saúde",
        "docs_url": SAUDE_DOCS_URL,
        "docs_env": "SAUDE_DOCS_URL",
        "csv_url": SAUDE_CSV_URL,
        "csv_env": "SAUDE_CSV_URL",
    },
    "economia-renda": {
        "nome": "Economia e Renda",
        "docs_url": ECONOMIA_RENDA_DOCS_URL,
        "docs_env": "ECONOMIA_RENDA_DOCS_URL",
        "csv_url": ECONOMIA_RENDA_CSV_URL,
        "csv_env": "ECONOMIA_RENDA_CSV_URL",
    },
    "saneamento": {
        "nome": "Saneamento",
        "docs_url": SANEAMENTO_DOCS_URL,
        "docs_env": "SANEAMENTO_DOCS_URL",
        "csv_url": SANEAMENTO_CSV_URL,
        "csv_env": "SANEAMENTO_CSV_URL",
    },
    "hidraulica": {
        "nome": "Hidráulica",
        "docs_url": HIDRAULICA_DOCS_URL,
        "docs_env": "HIDRAULICA_DOCS_URL",
        "csv_url": HIDRAULICA_CSV_URL,
        "csv_env": "HIDRAULICA_CSV_URL",
    },
}

MACROTEMA_SECOES = {
    "demografia": {
        "numero": "01",
        "titulo": "Demografia",
        "aliases": ["demografia"],
    },
    "educacao": {
        "numero": "02",
        "titulo": "Educação",
        "aliases": ["educacao", "educação"],
    },
    "saude": {
        "numero": "03",
        "titulo": "Saúde",
        "aliases": ["saude", "saúde"],
    },
    "economia-renda": {
        "numero": "04",
        "titulo": "Economia e Renda",
        "aliases": ["economia", "economia e renda"],
    },
    "saneamento": {
        "numero": "05",
        "titulo": "Infraestrutura e Saneamento",
        "aliases": ["saneamento", "infraestrutura e saneamento"],
    },
    "hidraulica": {
        "numero": "06",
        "titulo": "Segurança Hídrica",
        "aliases": ["hidraulica", "hidráulica", "seguranca hidrica", "segurança hídrica"],
    },
}


def resolve_csv_source(source: str | None, env_name: str = "CSV_URL") -> str | Path:
    if not source:
        raise HTTPException(
            status_code=500,
            detail=f"{env_name} não configurado. Defina no arquivo .config, .env ou nas variáveis de ambiente.",
        )

    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        return source

    csv_path = Path(source).expanduser()
    if not csv_path.is_absolute():
        csv_path = BASE_DIR / csv_path

    if not csv_path.exists():
        raise HTTPException(status_code=500, detail=f"Arquivo CSV não encontrado: {csv_path}")

    return csv_path


def require_config_value(value: str | None, env_name: str) -> str:
    if not value:
        raise HTTPException(
            status_code=500,
            detail=f"{env_name} não configurado. Defina no arquivo .config, .env ou nas variáveis de ambiente.",
        )
    return value


def get_macrotema(slug: str) -> dict[str, str]:
    macrotema = MACROTEMAS.get(slug)
    if not macrotema:
        validos = ", ".join(MACROTEMAS.keys())
        raise HTTPException(status_code=400, detail=f"Macrotema inválido. Use um destes: {validos}")
    return macrotema


def get_csv_config_for_macrotema(macrotema: dict[str, str | None]) -> tuple[str | None, str]:
    if macrotema["csv_url"]:
        return macrotema["csv_url"], macrotema["csv_env"]
    return DEMOGRAFIA_CSV_URL, "DEMOGRAFIA_CSV_URL"


def normalizar_colunas_macrotema(df: pd.DataFrame, namespace: str) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(coluna).lstrip("\ufeff").strip() for coluna in df.columns]

    if "nm_mun" not in df.columns and "city" in df.columns:
        df = df.rename(columns={"city": "nm_mun"})

    prefixo = f"{namespace}."
    colunas_renomeadas = {
        coluna: coluna[len(prefixo):]
        for coluna in df.columns
        if coluna.startswith(prefixo)
    }
    if colunas_renomeadas:
        df = df.rename(columns=colunas_renomeadas)

    return df

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
            font-family: Georgia, "Times New Roman", serif;
            max-width: 920px;
            margin: 32px auto;
            padding: 0 24px;
            line-height: 1.48;
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
            font-family: Arial, sans-serif;
            text-indent: 0;
        }
        .doc-content p.lead {
            font-family: Georgia, "Times New Roman", serif;
            font-size: 18px;
            font-style: italic;
            line-height: 1.38;
            color: #3d3d3d;
            margin: 10px 0 24px;
        }
        .doc-content h1 {
            font-size: 34px;
            font-weight: 700;
            margin: 0 0 18px 0;
        }
        .doc-content ul {
            text-indent: 0;
        }
        .section-heading {
            display: grid;
            grid-template-columns: auto 1fr;
            align-items: end;
            column-gap: 16px;
            margin: 14px 0 10px;
        }
        .section-number {
            color: #c68a2c;
            font-size: 56px;
            line-height: 0.9;
            font-weight: 400;
        }
        .section-title-wrap {
            padding-bottom: 7px;
            border-bottom: 1px solid #d99a37;
        }
        .section-title {
            color: #255235;
            font-size: 29px;
            line-height: 1;
            font-weight: 400;
        }
        .chart-block {
            margin: 18px auto 20px;
            text-align: center;
            break-inside: avoid;
        }
        .chart-block img {
            display: block;
            max-width: 78%;
            height: auto;
            margin: 0 auto;
        }
        .figure-caption {
            margin: 8px auto 16px;
            max-width: 76%;
            color: #333;
            font-family: Arial, sans-serif;
            font-size: 13px;
            line-height: 1.35;
            text-align: center;
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
    parsed = urlparse(valor)
    if not parsed.scheme and "/" not in valor:
        return valor

    partes = [p for p in parsed.path.split("/") if p]
    if "d" in partes:
        idx = partes.index("d")
        if idx + 1 < len(partes):
            return partes[idx + 1]
    raise ValueError("Não foi possível extrair o ID do Google Docs.")


def linha_parece_comentario_docs(linha: str) -> bool:
    linha_limpa = linha.strip()
    if not linha_limpa:
        return False

    if re.match(r"^\[[A-Za-z0-9]{1,3}\]", linha_limpa):
        return True

    marcador_no_inicio = re.match(r"^\[[A-Za-z0-9]{1,3}\]\s+", linha_limpa)
    palavras_de_comentario = re.search(
        r"\b(coment[aá]rio|comment|resolvido|resolved|reply|responder)\b",
        linha_limpa,
        flags=re.IGNORECASE,
    )
    comentario_com_autor = re.match(r"^\[[A-Za-z0-9]{1,3}\]\s*[^:]{1,80}:\s+", linha_limpa)
    return bool(marcador_no_inicio and (palavras_de_comentario or comentario_com_autor))


def limpar_texto_exportado_docs(texto: str) -> str:
    linhas_limpas = []
    for linha in texto.splitlines():
        if linha_parece_comentario_docs(linha):
            continue

        linha_sem_marcador = re.sub(r"(?<!\S)\[[A-Za-z0-9]{1,3}\](?!\S)", "", linha).rstrip()
        linhas_limpas.append(linha_sem_marcador)

    return "\n".join(linhas_limpas)


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
        raise ValueError(f"Erro ao exportar Google Docs ({err.code}). Verifique o link e as permissões.") from err
    except (URLError, TimeoutError) as err:
        raise ValueError("Não foi possível acessar o Google Docs. Verifique a conexão, o link e as permissões.") from err
    
    return limpar_texto_exportado_docs(texto)

def render_chart_placeholder(chart_file: str) -> str:
    return (
        '<div class="chart-block">'
        f'<img src="/output/{html.escape(chart_file)}" alt="Gráfico">'
        '</div>'
    )


def normalizar_titulo_para_match(texto: str) -> str:
    texto = re.sub(r"^\s*\d+\s*\.?\s*", "", texto).strip()
    texto = re.sub(r"\s+", " ", texto)
    return texto.casefold()


def identificar_secao_macrotema(linha: str, namespace: str) -> dict[str, object] | None:
    secao = MACROTEMA_SECOES.get(namespace)
    if not secao:
        return None

    titulo_normalizado = normalizar_titulo_para_match(linha)
    aliases = [alias.casefold() for alias in secao["aliases"]]
    if titulo_normalizado in aliases or secao["titulo"].casefold() == titulo_normalizado:
        return secao
    return None


def render_section_heading(secao: dict[str, object]) -> str:
    numero = html.escape(str(secao["numero"]))
    titulo = html.escape(str(secao["titulo"]))
    return (
        '<div class="section-heading">'
        f'<span class="section-number">{numero}</span>'
        f'<div class="section-title-wrap"><span class="section-title">{titulo}</span></div>'
        '</div>'
    )


def texto_para_html(
    texto: str,
    contexto: dict,
    namespace: str = "demografia",
    graficos_por_placeholder: dict[str, str] | None = None,
) -> str:
    def substituir_placeholder_dolar(match: re.Match) -> str:
        placeholder_namespace = match.group(1).lower()
        campo = match.group(2)
        namespaces_validos = {namespace.lower(), "linha", "dados", "csv"}
        if placeholder_namespace in namespaces_validos:
            return str(contexto.get(campo, match.group(0)))
        return match.group(0)

    alias_map = {
        "city": contexto.get("nm_mun", ""),
        "year": contexto.get("ano", ""),
        "municipio": contexto.get("nm_mun", ""),
        "ano": contexto.get("ano", ""),
        "data_relatorio": contexto.get("data_relatorio", ""),
        "hora_relatorio": contexto.get("hora_relatorio", ""),
        "data_geracao": contexto.get("data_relatorio", ""),
        "hora_geracao": contexto.get("hora_relatorio", ""),
    }
    graficos_por_placeholder = graficos_por_placeholder or {}

    texto_normalizado = texto
    texto_normalizado = re.sub(r"\$([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)", substituir_placeholder_dolar, texto_normalizado)
    for alias, valor in alias_map.items():
        texto_normalizado = texto_normalizado.replace(f"${alias}", str(valor))

    texto_renderizado = Environment().from_string(texto_normalizado).render(**contexto)
    linhas = [linha.rstrip() for linha in texto_renderizado.splitlines()]
    html_lines = []
    em_lista = False
    proximo_paragrafo_destaque = namespace in MACROTEMA_SECOES

    for linha in linhas:
        linha_limpa = linha.lstrip("\ufeff").strip()
        if not linha_limpa:
            if em_lista:
                html_lines.append("</ul>")
                em_lista = False
            continue

        marcador_grafico = re.fullmatch(r"%%([A-Za-z_][\w]*)", linha_limpa)
        if marcador_grafico:
            if em_lista:
                html_lines.append("</ul>")
                em_lista = False
            chart_file = graficos_por_placeholder.get(marcador_grafico.group(1))
            if chart_file:
                html_lines.append(render_chart_placeholder(chart_file))
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

        secao_macrotema = identificar_secao_macrotema(linha_limpa, namespace)
        if secao_macrotema:
            html_lines.append(render_section_heading(secao_macrotema))
            proximo_paragrafo_destaque = True
        elif re.match(r"^\d+\.\s+", linha_limpa) or linha_limpa.lower() in {"apresentação", "demografia"}:
            html_lines.append(f"<h2>{html.escape(linha_limpa)}</h2>")
            proximo_paragrafo_destaque = False
        elif re.match(r"^figura\s+[&x]\s*[–-]", linha_limpa, flags=re.IGNORECASE):
            legenda = re.sub(r"\[[A-Za-z0-9]{1,3}\]", "", linha_limpa).replace("&", "")
            html_lines.append(f'<p class="figure-caption">{html.escape(legenda.strip())}</p>')
            proximo_paragrafo_destaque = False
        else:
            linha_limpa = re.sub(r"\[[A-Za-z0-9]{1,3}\]", "", linha_limpa)
            classe = ' class="lead"' if proximo_paragrafo_destaque else ""
            html_lines.append(f"<p{classe}>{html.escape(linha_limpa)}</p>")
            proximo_paragrafo_destaque = False

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


@app.get("/macrotemas")
async def listar_macrotemas():
    return [
        {"slug": slug, "nome": dados["nome"]}
        for slug, dados in MACROTEMAS.items()
    ]

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
        macrotema = "Demografia"
        if "__" in slug_completo:
            primeira_parte, restante = slug_completo.split("__", 1)
            if primeira_parte in MACROTEMAS:
                slug_cidade = restante
                macrotema = MACROTEMAS[primeira_parte]["nome"]
            else:
                slug_cidade, _timestamp = slug_completo.rsplit("__", 1)
        else:
            slug_cidade = slug_completo

        cidade = re.sub(r"_+", " ", slug_cidade).strip().title()

        relatorios.append({
            "cidade": cidade,
            "macrotema": macrotema,
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
    chart_paths = [
        OUTPUT_DIR / f"grafico_sexo_{sufixo_relatorio}.png",
        OUTPUT_DIR / f"grafico_porte_{sufixo_relatorio}.png",
    ]

    removidos = []
    for caminho in [pdf_path, html_path, *chart_paths]:
        if caminho.exists() and caminho.is_file():
            caminho.unlink()
            removidos.append(caminho.name)

    if not removidos:
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")

    return {"ok": True, "removidos": removidos}

@app.get("/relatorio/{cidade}", response_class=HTMLResponse)
async def gerar_relatorio(cidade: str, macrotema: str = "demografia", charts: str = "all"):
    macrotema_dados = get_macrotema(macrotema)
    csv_url, csv_env = get_csv_config_for_macrotema(macrotema_dados)
    csv_source = resolve_csv_source(csv_url, csv_env)
    df = pd.read_csv(csv_source, delimiter=";")
    df = normalizar_colunas_macrotema(df, macrotema)
    
    try:
        linhas_df = filtrar_linhas_por_cidade(df, cidade)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

    linhas = linhas_df.to_dict("records")

    if not linhas:
        raise HTTPException(status_code=404, detail=f"Cidade '{cidade}' não encontrada.")

    gerado_em = datetime.now()
    for linha in linhas:
        linha["data_relatorio"] = gerado_em.strftime("%d/%m/%Y")
        linha["hora_relatorio"] = gerado_em.strftime("%H:%M")

    safe_city = re.sub(r"[^a-zA-Z0-9_-]+", "_", linhas[0]["nm_mun"].strip().lower())
    safe_report = f"{macrotema}__{safe_city}"

    # Charts plotting
    allowed = set(CHART_TYPES.keys())
    if charts == "all":
        to_generate = list(CHART_TYPES.keys()) if macrotema == "demografia" else []
    else:
        requested = [c.strip() for c in charts.split(",")]
        invalid = set(requested) - allowed
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo(s) de gráfico inválido(s): {invalid}. Tipos válidos: sexo, porte, top"
            )
        to_generate = requested
    graficos = []
    graficos_por_placeholder = {}
    for chart_type in to_generate:
        chart_func = CHART_TYPES[chart_type]
        if chart_type == "sexo":
            chart_file = chart_func(linhas[0], OUTPUT_DIR, safe_report)
        elif chart_type == "porte":
            chart_file = chart_func(df, OUTPUT_DIR, safe_report)
        elif chart_type == "top":
            chart_file = chart_func(df, OUTPUT_DIR)
        graficos.append(chart_file)
        graficos_por_placeholder[f"grafico_{chart_type}"] = chart_file

    docs_url = require_config_value(macrotema_dados["docs_url"], macrotema_dados["docs_env"])
    try:
        docs_texto = carregar_texto_do_docs(docs_url)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    docs_html = texto_para_html(
        docs_texto,
        linhas[0],
        namespace=macrotema,
        graficos_por_placeholder=graficos_por_placeholder,
    )

    # Template rendering
    template = Environment(trim_blocks=True, lstrip_blocks=True).from_string(TEMPLATE_STRING)
    html = template.render(dados=linhas, graficos=graficos, docs_html=docs_html)

    # Output file handling
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"relatorio_{safe_report}.html"
    output_file.write_text(html, encoding="utf-8")

    # Gerar PDF usando WeasyPrint
    pdf_file = OUTPUT_DIR / f"relatorio_{safe_report}.pdf"
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
