import logging
import re
import unicodedata
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import pandas as pd
from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from weasyprint import HTML

from config import (
    CARACTERISTICAS_DOCS_URL,
    OUTPUT_DIR,
    require_config_value,
    resolve_csv_source,
)
from plotting.educacao import gerar_grafico_cor_faixa_etaria
from utils.cities import filtrar_linhas_por_cidade
from utils.cover import montar_capa_relatorio
from utils.docs import (
    carregar_texto_do_docs,
    extrair_descricao_tema,
    extrair_diagnostico_cidade,
    extrair_inicio_relatorio,
    extrair_introducao,
    extrair_referencias,
    extrair_relatorio_geral,
    extrair_resumo_cidade,
    extrair_resumo_relatorio,
    extrair_resumo_tema,
    remover_titulos_docs,
)
from utils.macrotemas import MACROTEMAS, TODOS_MACROTEMAS_NOME, TODOS_MACROTEMAS_SLUG
from utils.renderer import (
    render_descricao_tema_html,
    render_mapa_marker,
    substituir_placeholders,
    texto_para_html,
)
from utils.ssr import render_react_ssr

logger = logging.getLogger(__name__)

_CSV_CACHE: dict[str, pd.DataFrame] = {}


def _gerar_pdf_sync(html_content: str, pdf_file: Path) -> None:
    try:
        pdf_html = re.sub(r'src="/output/', 'src="', html_content)
        HTML(string=pdf_html, base_url=str(OUTPUT_DIR.resolve())).write_pdf(str(pdf_file))
    except (OSError, RuntimeError, TypeError, ValueError) as e:
        logger.warning("Falha ao gerar PDF %s: %s", pdf_file, e)


async def _gerar_pdf(html_content: str, pdf_file: Path) -> None:
    import asyncio
    await asyncio.to_thread(_gerar_pdf_sync, html_content, pdf_file)


def _carregar_csv(csv_source: str | Path) -> pd.DataFrame:
    cache_key = str(csv_source)
    if cache_key in _CSV_CACHE:
        return _CSV_CACHE[cache_key].copy()
    conteudo_bytes = None
    if isinstance(csv_source, str) and csv_source.startswith(("http://", "https://")):
        request = Request(csv_source, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=30) as response:
            conteudo_bytes = response.read()
    for sep in (",", ";"):
        fonte = BytesIO(conteudo_bytes) if conteudo_bytes is not None else csv_source
        try:
            df = pd.read_csv(fonte, sep=sep, engine="c")
            if len(df.columns) > 1:
                break
        except (pd.errors.ParserError, ValueError):
            continue
    _CSV_CACHE[cache_key] = df.copy()
    return df


def get_macrotema(slug: str) -> dict[str, str]:
    macrotema = MACROTEMAS.get(slug)
    if not macrotema:
        validos = ", ".join([TODOS_MACROTEMAS_SLUG, *MACROTEMAS.keys()])
        raise HTTPException(status_code=400, detail=f"Macrotema inválido. Use um destes: {validos}")
    return macrotema


def get_macrotema_slugs_para_relatorio(macrotema: str) -> list[str]:
    if macrotema == TODOS_MACROTEMAS_SLUG:
        return list(MACROTEMAS.keys())
    slugs = [slug.strip() for slug in macrotema.split(",") if slug.strip()]
    if not slugs:
        return ["demografia"]
    slugs_unicos: list[str] = []
    for slug in slugs:
        if slug == TODOS_MACROTEMAS_SLUG:
            return list(MACROTEMAS.keys())
        get_macrotema(slug)
        if slug not in slugs_unicos:
            slugs_unicos.append(slug)
    return slugs_unicos


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
        # use a fixed local timezone to present dates consistently across deployments
        local_tz = ZoneInfo("America/Fortaleza")
        criado_em = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).astimezone(local_tz)
        pdf_version = stat.st_mtime_ns
        html_version = html_file.stat().st_mtime_ns if html_file.exists() else None
        mapa_version = mapa_file.stat().st_mtime_ns if mapa_file.exists() else None

        macrotema = "Demografia"
        if "__" in slug_completo:
            primeira_parte, restante = slug_completo.split("__", 1)
            if primeira_parte == TODOS_MACROTEMAS_SLUG:
                slug_cidade = restante
                macrotema = TODOS_MACROTEMAS_NOME
            else:
                slugs_encontrados = [
                    slug for slug in primeira_parte.split("_")
                    if slug in MACROTEMAS
                ]
                if slugs_encontrados and "_".join(slugs_encontrados) == primeira_parte:
                    slug_cidade = restante
                    macrotema = ", ".join(
                        MACROTEMAS[slug]["nome"] for slug in slugs_encontrados
                    )
                elif primeira_parte in MACROTEMAS:
                    slug_cidade = restante
                    macrotema = MACROTEMAS[primeira_parte]["nome"]
                else:
                    slug_cidade, _timestamp = slug_completo.rsplit("__", 1)
        else:
            slug_cidade = slug_completo

        cidade = re.sub(r"_+", " ", slug_cidade).strip().title()

        # compute stable timestamps for both UTC and local timezone
        last_modified_utc = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        last_modified_local = last_modified_utc.astimezone(local_tz)

        relatorios.append({
            "cidade": cidade,
            "macrotema": macrotema,
            "arquivo_pdf": pdf_file.name,
            "arquivo_html": html_file.name if html_file.exists() else None,
            "arquivo_mapa": mapa_file.name if mapa_file.exists() else None,
            "data": criado_em.strftime("%d/%m/%Y"),
            "hora": criado_em.strftime("%H:%M:%S"),
            "last_modified_utc": last_modified_utc.isoformat(),
            "last_modified_local": last_modified_local.isoformat(),
            # preformatted display fields (local timezone) to avoid client/SSR
            # formatting inconsistencies across deployments
            "display_date": last_modified_local.strftime("%d/%m/%Y"),
            "display_time": last_modified_local.strftime("%H:%M:%S"),
            "pdf_url": f"/output/v{pdf_version}/{pdf_file.name}",
            "html_url": (
                f"/output/v{html_version}/{html_file.name}"
                if html_version is not None else None
            ),
            "mapa_url": (
                f"/output/v{mapa_version}/{mapa_file.name}"
                if mapa_version is not None else None
            ),
        })

    # sort by the ISO UTC timestamp so ordering is unambiguous
    relatorios.sort(key=lambda item: item.get("last_modified_utc", ""), reverse=True)

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


async def gerar_relatorio_handler(cidade: str, macrotema: str = "demografia"):
    macrotema_slugs = get_macrotema_slugs_para_relatorio(macrotema)
    gerado_em = datetime.now().astimezone()

    linhas = None
    cover = None
    safe_city = None
    safe_report = None
    macrotemas_render: list[dict[str, object]] = []
    docs_html_parts = []
    caracteristicas_html_parts: list[str] = []
    resumo_relatorio_html_parts: list[str] = []
    resumo_relatorio_parts: list[str] = []
    referencias: list[str] = []

    for macrotema_slug in macrotema_slugs:
        macrotema_dados = get_macrotema(macrotema_slug)

        if not macrotema_dados["docs_url"]:
            logger.warning(
                "Macrotema '%s' não possui docs_url configurado (%s). Pulando.",
                macrotema_slug,
                macrotema_dados["docs_env"],
            )
            continue
        csv_url, csv_env = get_csv_config_for_macrotema(macrotema_dados)
        csv_source = resolve_csv_source(csv_url, csv_env)
        df = _carregar_csv(csv_source)
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
            cover["macrotemas"] = macrotemas_render
            safe_city = re.sub(r"[^a-zA-Z0-9_-]+", "_", cidade.strip().lower())
            primeiro_slug = macrotema_slugs[0]
            if macrotema == TODOS_MACROTEMAS_SLUG:
                slug_arquivo = TODOS_MACROTEMAS_SLUG
            elif "," in macrotema:
                slug_arquivo = "_".join(
                    slug for slug in macrotema_slugs if slug != TODOS_MACROTEMAS_SLUG
                ) or primeiro_slug
            else:
                slug_arquivo = macrotema.split(",")[0].strip()
            safe_report = f"{slug_arquivo}__{safe_city}"

            if CARACTERISTICAS_DOCS_URL:
                # O documento de Características Gerais é comum a todos os
                # macrotemas, mas seus placeholders ainda precisam dos dados da
                # cidade do relatório. Usar um contexto vazio fazia campos como
                # caract_mun.$nm_mun permanecerem sem resolução, especialmente
                # quando o relatório era iniciado por Economia e Renda.
                contexto_caracteristicas = linhas_macrotema[0]
                try:
                    caracteristicas_texto = await carregar_texto_do_docs(
                        CARACTERISTICAS_DOCS_URL
                    )
                except ValueError as err:
                    raise HTTPException(status_code=400, detail=str(err)) from err

                inicio_relatorio, caracteristicas_texto = extrair_inicio_relatorio(
                    caracteristicas_texto
                )
                if inicio_relatorio:
                    linhas_inicio = [
                        linha.strip()
                        for linha in inicio_relatorio.splitlines()
                        if linha.strip()
                    ]
                    cover["inicio_relatorio"] = linhas_inicio[0]
                    if len(linhas_inicio) > 1:
                        cover["inicio_relatorio_subtitulo"] = substituir_placeholders(
                            " ".join(linhas_inicio[1:]),
                            contexto_caracteristicas,
                            "caract_mun",
                        )

                introducao, caracteristicas_texto = extrair_introducao(
                    caracteristicas_texto
                )
                if introducao:
                    link_data_nordeste = re.search(
                        r"(?im)^\s*(https://datanordeste\.sudene\.gov\.br/?)\s*$",
                        caracteristicas_texto,
                    )
                    if link_data_nordeste:
                        introducao = f"{introducao}\n\n{link_data_nordeste.group(1)}"
                        caracteristicas_texto = (
                            caracteristicas_texto[:link_data_nordeste.start()]
                            + caracteristicas_texto[link_data_nordeste.end():]
                        ).strip()
                    cover["introducao_html"] = render_descricao_tema_html(
                        introducao,
                        contexto_caracteristicas,
                        namespace="caract_mun",
                        safe_report=safe_report,
                    )
                    cover["introducao"] = substituir_placeholders(
                        introducao, contexto_caracteristicas, "caract_mun"
                    )

                relatorio_geral, caracteristicas_texto = extrair_relatorio_geral(
                    caracteristicas_texto
                )
                if relatorio_geral:
                    cover["relatorio_geral_html"] = render_descricao_tema_html(
                        relatorio_geral,
                        contexto_caracteristicas,
                        namespace="caract_mun",
                        safe_report=safe_report,
                    )
                    cover["relatorio_geral"] = substituir_placeholders(
                        relatorio_geral, contexto_caracteristicas, "caract_mun"
                    )

                resumo_cidade, caracteristicas_texto = extrair_resumo_cidade(
                    caracteristicas_texto
                )
                if resumo_cidade:
                    cover["resumo_cidade_html"] = render_descricao_tema_html(
                        resumo_cidade,
                        contexto_caracteristicas,
                        namespace="caract_mun",
                        safe_report=safe_report,
                    )
                    cover["resumo_cidade"] = substituir_placeholders(
                        resumo_cidade, contexto_caracteristicas, "caract_mun"
                    )

                resumo_relatorio, caracteristicas_texto = extrair_resumo_relatorio(
                    caracteristicas_texto
                )
                if resumo_relatorio:
                    resumo_relatorio_html_parts.extend(
                        render_descricao_tema_html(
                            resumo_relatorio,
                            contexto_caracteristicas,
                            namespace="caract_mun",
                            safe_report=safe_report,
                        )
                    )
                    resumo_relatorio_parts.append(
                        substituir_placeholders(
                            resumo_relatorio,
                            contexto_caracteristicas,
                            "caract_mun",
                        )
                    )

                referencias_comuns, caracteristicas_texto = extrair_referencias(
                    caracteristicas_texto
                )
                referencias.extend(referencias_comuns)
                caracteristicas_texto = remover_titulos_docs(
                    caracteristicas_texto,
                    "Apresentação",
                    "Apresentacao",
                    "Aoresentacao",
                    "Características Gerais",
                    "Relatório Personalizado",
                    "caract_mun.$nm_mun (caract_mun.$sigla_uf) EM DADOS",
                    "Referências",
                )

                caracteristicas_html_parts.append(
                    texto_para_html(
                        caracteristicas_texto,
                        contexto_caracteristicas,
                        namespace="caract_mun",
                        safe_report=safe_report,
                    )
                )

        graficos_por_placeholder = {}

        if macrotema_slug == "educacao":
            cidade_series = pd.Series(linhas_macrotema[0])
            chart_file_name = gerar_grafico_cor_faixa_etaria(
                cidade=cidade_series,
                OUTPUT_DIR=OUTPUT_DIR,
                safe_city=safe_city or "relatorio",
            )
            graficos_por_placeholder["grafico_cor_faixa_etaria"] = chart_file_name

        docs_url = require_config_value(macrotema_dados["docs_url"], macrotema_dados["docs_env"])
        try:
            docs_texto = await carregar_texto_do_docs(docs_url)
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err)) from err

        eh_primeiro = macrotema_slug == macrotema_slugs[0]

        macrotema_item: dict[str, object] = {
            "nome": macrotema_dados["nome"],
            "slug": macrotema_slug,
            "icone": cover["macrotema"]["icone"],
            "cor": cover["macrotema"]["cor"],
            "resumo": "",
            "descricao": "",
            "descricao_paragrafos": [],
            "descricao_html": [],
            "score": cover["macrotema"]["score"],
            "indicadores": cover["macrotema"]["indicadores"],
        }

        resumo_tema, docs_texto = extrair_resumo_tema(docs_texto)
        if resumo_tema:
            macrotema_item["resumo"] = substituir_placeholders(
                resumo_tema, linhas_macrotema[0], macrotema_slug
            )
            if eh_primeiro and cover is not None:
                cover["macrotema"]["resumo"] = macrotema_item["resumo"]

        relatorio_geral, docs_texto = extrair_relatorio_geral(docs_texto)
        if relatorio_geral and eh_primeiro and cover is not None:
            cover["relatorio_geral_html"] = render_descricao_tema_html(
                relatorio_geral,
                linhas_macrotema[0],
                namespace=macrotema_slug,
                safe_report=safe_report,
            )
            cover["relatorio_geral"] = substituir_placeholders(
                relatorio_geral, linhas_macrotema[0], macrotema_slug
            )

        # O resumo do relatório é global e vem do documento de Características.
        # Removemos uma eventual cópia antiga do documento do macrotema para que
        # ela não seja renderizada nem concorra com a fonte comum.
        _, docs_texto = extrair_resumo_relatorio(docs_texto)

        referencias_macrotema, docs_texto = extrair_referencias(docs_texto)
        referencias.extend(referencias_macrotema)
        docs_texto = remover_titulos_docs(
            docs_texto,
            "Apresentação",
            "Apresentacao",
            "Aoresentacao",
            "Referências",
        )

        resumo_cidade, docs_texto = extrair_resumo_cidade(docs_texto)
        if resumo_cidade and eh_primeiro and cover is not None:
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
        if diagnostico_cidade and eh_primeiro and cover is not None:
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
        if descricao_tema:
            macrotema_item["descricao"] = substituir_placeholders(
                descricao_tema, linhas_macrotema[0], macrotema_slug
            )
            macrotema_item["descricao_paragrafos"] = [
                substituir_placeholders(
                    paragrafo.strip(), linhas_macrotema[0], macrotema_slug
                )
                for paragrafo in re.split(r"\n\s*\n", descricao_tema)
                if paragrafo.strip()
            ]
            macrotema_item["descricao_html"] = render_descricao_tema_html(
                descricao_tema,
                linhas_macrotema[0],
                namespace=macrotema_slug,
                safe_report=safe_report,
                graficos_por_placeholder=graficos_por_placeholder,
            )
            if eh_primeiro and cover is not None:
                cover["macrotema"]["descricao"] = macrotema_item["descricao"]
                cover["macrotema"]["descricao_paragrafos"] = macrotema_item["descricao_paragrafos"]
                cover["macrotema"]["descricao_html"] = macrotema_item["descricao_html"]

        if eh_primeiro and cover is not None:
            cover["mapa_principal"] = render_mapa_marker(
                linhas_macrotema[0], safe_report
            )

        macrotemas_render.append(macrotema_item)

        docs_html_parts.append(
            texto_para_html(
                docs_texto,
                linhas_macrotema[0],
                namespace=macrotema_slug,
                graficos_por_placeholder=graficos_por_placeholder,
                safe_report=safe_report,
            )
        )

    referencias_unicas = {
        re.sub(r"\s+", " ", referencia).strip(): None
        for referencia in referencias
        if referencia.strip()
    }

    def chave_referencia(referencia: str) -> str:
        texto_sem_acentos = "".join(
            caractere
            for caractere in unicodedata.normalize("NFKD", referencia)
            if not unicodedata.combining(caractere)
        )
        return texto_sem_acentos.casefold()

    referencias_ordenadas = sorted(referencias_unicas, key=chave_referencia)
    if referencias_ordenadas:
        referencias_texto = "#! Referências\n\n" + "\n\n".join(
            referencias_ordenadas
        )
        docs_html_parts.append(
            texto_para_html(
                referencias_texto,
                {},
                namespace="caract_mun",
                safe_report=safe_report,
            )
        )

    docs_html = "\n".join([*caracteristicas_html_parts, *docs_html_parts])

    if cover is not None:
        cover["resumo_relatorio_html"] = resumo_relatorio_html_parts
        cover["resumo_relatorio"] = "\n\n".join(resumo_relatorio_parts)

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

    # Gerar PDF em background sempre, para manter o artefato sincronizado com o HTML
    # e evitar reaproveitar um PDF antigo quando os dados/mapas mudarem no mesmo dia.
    pdf_file = OUTPUT_DIR / f"relatorio_{safe_report}.pdf"

    for stale_artifact in (pdf_file, output_file):
        try:
            stale_artifact.unlink()
        except FileNotFoundError:
            pass

    await _gerar_pdf(html_content, pdf_file)

    return HTMLResponse(content=html_content)
