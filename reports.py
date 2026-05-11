import re
import pandas as pd
from datetime import datetime
from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from jinja2 import Environment
from weasyprint import HTML
from config import BASE_DIR, OUTPUT_DIR, resolve_csv_source, require_config_value
from utils.macrotemas import MACROTEMAS
from utils.cities import filtrar_linhas_por_cidade
from utils.docs import carregar_texto_do_docs
from utils.renderer import texto_para_html, TEMPLATE_STRING, FALLBACK_DOC_TEXT
from plotting import gerar_grafico_sexo
from plotting import gerar_grafico_porte
from plotting import gerar_grafico_top_cidades


CHART_TYPES = {
    "sexo": gerar_grafico_sexo,
    "porte": gerar_grafico_porte,
    "top": gerar_grafico_top_cidades,
}


def get_macrotema(slug: str) -> dict[str, str]:
    macrotema = MACROTEMAS.get(slug)
    if not macrotema:
        validos = ", ".join(MACROTEMAS.keys())
        raise HTTPException(status_code=400, detail=f"Macrotema inválido. Use um destes: {validos}")
    return macrotema


def get_csv_config_for_macrotema(macrotema: dict[str, str | None]) -> tuple[str | None, str]:
    if macrotema["csv_url"]:
        return macrotema["csv_url"], macrotema["csv_env"]
    return MACROTEMAS["demografia"]["csv_url"], "DEMOGRAFIA_CSV_URL"


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


async def listar_relatorios_handler():
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
                partes_restantes = restante.rsplit("__", 1)
                slug_cidade = partes_restantes[0]
                macrotema = MACROTEMAS[primeira_parte]["nome"]
            else:
                slug_cidade = slug_completo
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


async def apagar_relatorio_handler(arquivo_pdf: str):
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
        OUTPUT_DIR / f"grafico_top_{sufixo_relatorio}.png",
    ]

    removidos = []
    for caminho in [pdf_path, html_path, *chart_paths]:
        if caminho.exists() and caminho.is_file():
            caminho.unlink()
            removidos.append(caminho.name)

    if not removidos:
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")

    return {"ok": True, "removidos": removidos}


async def gerar_relatorio_handler(cidade: str, macrotema: str = "demografia", charts: str = "all"):
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

    timestamp = gerado_em.strftime("%Y%m%d_%H%M%S")
    safe_report = f"{macrotema}__{safe_city}__{timestamp}"

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

        try:
            if chart_type == "sexo":
                chart_file = chart_func(linhas[0], OUTPUT_DIR, safe_report)
            elif chart_type == "porte":
                chart_file = chart_func(df, OUTPUT_DIR, safe_report)
            elif chart_type == "top":
                chart_file = chart_func(df, OUTPUT_DIR)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao gerar gráfico '{chart_type}': {exc}"
            ) from exc
        graficos.append(chart_file)
        graficos_por_placeholder[f"grafico_{chart_type}"] = chart_file

    docs_url = require_config_value(macrotema_dados["docs_url"], macrotema_dados["docs_env"])
    try:
        docs_texto = carregar_texto_do_docs(docs_url)
    except ValueError as err:

        docs_texto = FALLBACK_DOC_TEXT

    docs_html = texto_para_html(
        docs_texto,
        linhas[0],
        namespace=macrotema,
        graficos_por_placeholder=graficos_por_placeholder,
    )

    # Template rendering
    template = Environment(trim_blocks=True, lstrip_blocks=True).from_string(TEMPLATE_STRING)

    html_content = template.render(dados=linhas, graficos=graficos, docs_html=docs_html)

    # Output file handling
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"relatorio_{safe_report}.html"
    output_file.write_text(html_content, encoding="utf-8")

    # Gerar PDF usando WeasyPrint
    pdf_file = OUTPUT_DIR / f"relatorio_{safe_report}.pdf"
    HTML(string=html_content, base_url=str(OUTPUT_DIR.resolve())).write_pdf(str(pdf_file))

    return HTMLResponse(content=html_content)