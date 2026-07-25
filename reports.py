import logging
import re
import pandas as pd
from datetime import datetime
from fastapi import BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse
from weasyprint import HTML
from pathlib import Path

from config import OUTPUT_DIR, resolve_csv_source, require_config_value
from utils.macrotemas import MACROTEMAS, TODOS_MACROTEMAS_NOME, TODOS_MACROTEMAS_SLUG
from utils.cities import filtrar_linhas_por_cidade
from utils.docs import (
    carregar_texto_do_docs,
    extrair_descricao_tema,
    extrair_resumo_tema,
    extrair_relatorio_geral,
    extrair_resumo_relatorio,
    extrair_resumo_cidade,
    extrair_diagnostico_cidade,
)
from utils.cover import montar_capa_relatorio
from utils.renderer import render_descricao_tema_html, render_mapa_marker, substituir_placeholders, texto_para_html
from utils.ssr import render_react_ssr
from plotting import gerar_grafico_sexo
from plotting import gerar_grafico_porte
from plotting import gerar_grafico_top_cidades


logger = logging.getLogger(__name__)

_CSV_CACHE: dict[str, pd.DataFrame] = {}


def _gerar_pdf(html_content: str, pdf_file: Path) -> None:
    try:
        pdf_html = re.sub(r'src="/output/', 'src="', html_content)
        HTML(string=pdf_html, base_url=str(OUTPUT_DIR.resolve())).write_pdf(str(pdf_file))
    except Exception as e:
        logger.warning("Falha ao gerar PDF %s: %s", pdf_file, e)


def _carregar_csv(csv_source: str | Path) -> pd.DataFrame:
    cache_key = str(csv_source)
    if cache_key in _CSV_CACHE:
        return _CSV_CACHE[cache_key].copy()
    df = pd.read_csv(csv_source, delimiter=";")
    _CSV_CACHE[cache_key] = df.copy()
    return df


CHART_TYPES = {
    "sexo": gerar_grafico_sexo,
    "porte": gerar_grafico_porte,
    "top": gerar_grafico_top_cidades,
}


def get_macrotema(slug: str) -> dict[str, str]:
    macrotema = MACROTEMAS.get(slug)
    if not macrotema:
        validos = ", ".join([TODOS_MACROTEMAS_SLUG, *MACROTEMAS.keys()])
        raise HTTPException(status_code=400, detail=f"Macrotema inválido. Use um destes: {validos}")
    return macrotema


def get_macrotema_slugs_para_relatorio(macrotema: str) -> list[str]:
    if macrotema == TODOS_MACROTEMAS_SLUG:
        return list(MACROTEMAS.keys())
    get_macrotema(macrotema)
    return [macrotema]


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
        slug_completo = nome_base.replace("relatorio_", "", 1)
        mapa_file = OUTPUT_DIR / f"mapa_regiao_{slug_completo}.png"

        stat = pdf_file.stat()
        criado_em = datetime.fromtimestamp(stat.st_mtime)

        macrotema = "Demografia"
        if "__" in slug_completo:
            primeira_parte, restante = slug_completo.split("__", 1)
            if primeira_parte == TODOS_MACROTEMAS_SLUG:
                slug_cidade = restante
                macrotema = TODOS_MACROTEMAS_NOME
            elif primeira_parte in MACROTEMAS:
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
            "arquivo_mapa": mapa_file.name if mapa_file.exists() else None,
            "data": criado_em.strftime("%d/%m/%Y"),
            "hora": criado_em.strftime("%H:%M:%S"),
            "pdf_url": f"/output/{pdf_file.name}",
            "html_url": f"/output/{html_file.name}" if html_file.exists() else None,
            "mapa_url": f"/output/{mapa_file.name}" if mapa_file.exists() else None,
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
        OUTPUT_DIR / f"mapa_regiao_{sufixo_relatorio}.png",
    ]

    removidos = []
    for caminho in [pdf_path, html_path, *chart_paths]:
        if caminho.exists() and caminho.is_file():
            caminho.unlink()
            removidos.append(caminho.name)

    if not removidos:
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")

    return {"ok": True, "removidos": removidos}


async def gerar_relatorio_handler(cidade: str, macrotema: str = "demografia", charts: str = "all", *, background_tasks: BackgroundTasks):
    macrotema_slugs = get_macrotema_slugs_para_relatorio(macrotema)
    gerado_em = datetime.now()
    allowed = set(CHART_TYPES.keys())
    requested_charts = list(CHART_TYPES.keys()) if charts == "all" else [c.strip() for c in charts.split(",")]
    invalid = set(requested_charts) - allowed
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo(s) de gráfico inválido(s): {invalid}. Tipos válidos: sexo, porte, top"
        )

    linhas = None
    cover = None
    safe_city = None
    safe_report = None
    graficos = []
    docs_html_parts = []

    for macrotema_slug in macrotema_slugs:
        macrotema_dados = get_macrotema(macrotema_slug)
        csv_url, csv_env = get_csv_config_for_macrotema(macrotema_dados)
        csv_source = resolve_csv_source(csv_url, csv_env)
        df = pd.read_csv(csv_source, delimiter=";")
        df = normalizar_colunas_macrotema(df, macrotema_slug)

        try:
            linhas_df = filtrar_linhas_por_cidade(df, cidade)
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))

        linhas_macrotema = linhas_df.to_dict("records")

        if not linhas_macrotema:
            raise HTTPException(status_code=404, detail=f"Cidade '{cidade}' não encontrada.")

        for linha in linhas_macrotema:
            linha["data_relatorio"] = gerado_em.strftime("%d/%m/%Y")
            linha["hora_relatorio"] = gerado_em.strftime("%H:%M")

        if linhas is None:
            linhas = linhas_macrotema
            cover = montar_capa_relatorio(
                linhas[0],
                gerado_em,
                macrotema_dados["nome"],
                macrotema_slug,
            )
            safe_city = re.sub(r"[^a-zA-Z0-9_-]+", "_", linhas[0]["nm_mun"].strip().lower())
            safe_report = f"{macrotema}__{safe_city}"

        graficos_por_placeholder = {}
        if macrotema_slug == "demografia":
            for chart_type in requested_charts:
                chart_func = CHART_TYPES[chart_type]
                if chart_type == "sexo":
                    chart_file = chart_func(linhas_macrotema[0], OUTPUT_DIR, safe_report)
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

        resumo_tema, docs_texto = extrair_resumo_tema(docs_texto)
        if resumo_tema and cover is not None and macrotema_slug == macrotema_slugs[0]:
            cover["macrotema"]["resumo"] = substituir_placeholders(
                resumo_tema, linhas_macrotema[0], macrotema_slug
            )

        relatorio_geral, docs_texto = extrair_relatorio_geral(docs_texto)
        if relatorio_geral and cover is not None and macrotema_slug == macrotema_slugs[0]:
            cover["relatorio_geral_html"] = render_descricao_tema_html(
                relatorio_geral,
                linhas_macrotema[0],
                namespace=macrotema_slug,
                safe_report=safe_report,
            )
            cover["relatorio_geral"] = substituir_placeholders(
                relatorio_geral, linhas_macrotema[0], macrotema_slug
            )

        resumo_relatorio, docs_texto = extrair_resumo_relatorio(docs_texto)
        if resumo_relatorio and cover is not None and macrotema_slug == macrotema_slugs[0]:
            cover["resumo_relatorio_html"] = render_descricao_tema_html(
                resumo_relatorio,
                linhas_macrotema[0],
                namespace=macrotema_slug,
                safe_report=safe_report,
            )
            cover["resumo_relatorio"] = substituir_placeholders(
                resumo_relatorio, linhas_macrotema[0], macrotema_slug
            )

        resumo_cidade, docs_texto = extrair_resumo_cidade(docs_texto)
        if resumo_cidade and cover is not None and macrotema_slug == macrotema_slugs[0]:
            cover["resumo_cidade_html"] = render_descricao_tema_html(
                resumo_cidade,
                linhas_macrotema[0],
                namespace=macrotema_slug,
                safe_report=safe_report,
            )
            cover["resumo_cidade"] = substituir_placeholders(
                resumo_cidade, linhas_macrotema[0], macrotema_slug
            )

        diagnostico_cidade, docs_texto = extrair_diagnostico_cidade(docs_texto)
        if diagnostico_cidade and cover is not None and macrotema_slug == macrotema_slugs[0]:
            cover["diagnostico_cidade_html"] = render_descricao_tema_html(
                diagnostico_cidade,
                linhas_macrotema[0],
                namespace=macrotema_slug,
                safe_report=safe_report,
            )
            cover["diagnostico_cidade"] = substituir_placeholders(
                diagnostico_cidade, linhas_macrotema[0], macrotema_slug
            )

        descricao_tema, docs_texto = extrair_descricao_tema(docs_texto)
        if descricao_tema and cover is not None and macrotema_slug == macrotema_slugs[0]:
            cover["macrotema"]["descricao"] = substituir_placeholders(
                descricao_tema, linhas_macrotema[0], macrotema_slug
            )
            cover["macrotema"]["descricao_paragrafos"] = [
                substituir_placeholders(
                    paragrafo.strip(), linhas_macrotema[0], macrotema_slug
                )
                for paragrafo in re.split(r"\n\s*\n", descricao_tema)
                if paragrafo.strip()
            ]
            cover["macrotema"]["descricao_html"] = render_descricao_tema_html(
                descricao_tema,
                linhas_macrotema[0],
                namespace=macrotema_slug,
                safe_report=safe_report,
            )

        mapa_principal = None
        for paragrafo in re.split(r"\n\s*\n", docs_texto):
            if paragrafo.strip().lower() in {"*mapa_geografico", "mapa_geografico"}:
                if cover is not None and macrotema_slug == macrotema_slugs[0]:
                    mapa_principal = render_mapa_marker(linhas_macrotema[0], safe_report)
                break

        if mapa_principal and cover is not None:
            cover["mapa_principal"] = mapa_principal

        docs_texto_sem_mapa = re.sub(
            r"(?im)^\s*\*?mapa_geografico\s*$", "", docs_texto
        ).strip()

        docs_html_parts.append(
            texto_para_html(
                docs_texto_sem_mapa,
                linhas_macrotema[0],
                namespace=macrotema_slug,
                graficos_por_placeholder=graficos_por_placeholder,
                safe_report=safe_report,
            )
        )

    docs_html = "\n".join(docs_html_parts)

    # React SSR rendering
    html_content = await render_react_ssr({
        "cover": cover,
        "docsHtml": docs_html,
        "dados": linhas,
    })

    # Output file handling
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"relatorio_{safe_report}.html"
    output_file.write_text(html_content, encoding="utf-8")

    # Gerar PDF em background
    pdf_file = OUTPUT_DIR / f"relatorio_{safe_report}.pdf"
    if not pdf_file.exists():
        background_tasks.add_task(_gerar_pdf, html_content, pdf_file)

    return HTMLResponse(content=html_content)
