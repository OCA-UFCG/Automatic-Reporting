import logging
import re
import unicodedata
from datetime import datetime

from fastapi import HTTPException
from fastapi.responses import HTMLResponse

from config import (
    CARACTERISTICAS_DOCS_URL,
    OUTPUT_DIR,
    require_config_value,
    resolve_csv_source,
)
from services.csv_loader import (
    carregar_csv,
    get_csv_config_for_macrotema,
    normalizar_colunas_macrotema,
)
from services.macrotemas import get_macrotema, get_macrotema_slugs_para_relatorio
from services.pdf import _gerar_pdf
from utils.cover import montar_capa_relatorio
from utils.data.cities import filtrar_linhas_por_cidade
from utils.data.macrotemas import TODOS_MACROTEMAS_SLUG
from utils.external.docs import (
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
from utils.render.renderer import (
    render_descricao_tema_html,
    render_mapa_marker,
    substituir_placeholders,
    texto_para_html,
)
from utils.ssr import render_react_ssr

logger = logging.getLogger(__name__)


async def gerar_relatorio_handler(cidade: str, macrotema: str = "demografia"):
    try:
        macrotema_slugs = get_macrotema_slugs_para_relatorio(macrotema)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
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
        try:
            macrotema_dados = get_macrotema(macrotema_slug)
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))

        if not macrotema_dados["docs_url"]:
            logger.warning(
                "Macrotema '%s' não possui docs_url configurado (%s). Pulando.",
                macrotema_slug,
                macrotema_dados["docs_env"],
            )
            continue
        csv_url, csv_env = get_csv_config_for_macrotema(macrotema_dados)
        csv_source = resolve_csv_source(csv_url, csv_env)
        df = carregar_csv(csv_source)
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
            cover["macrotemas_tags"] = [
                {
                    "nome": get_macrotema(slug)["nome"],
                    "slug": slug,
                    "cor": get_macrotema(slug)["cor"],
                }
                for slug in macrotema_slugs
            ]
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

        docs_url = require_config_value(macrotema_dados["docs_url"], macrotema_dados["docs_env"])
        try:
            docs_texto = await carregar_texto_do_docs(docs_url)
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err)) from err

        eh_primeiro = macrotema_slug == macrotema_slugs[0]

        macrotema_item: dict[str, object] = {
            "nome": macrotema_dados["nome"],
            "slug": macrotema_slug,
            "icone": macrotema_dados["icone"],
            "cor": macrotema_dados["cor"],
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

    if not await _gerar_pdf(html_content, pdf_file):
        raise HTTPException(
            status_code=500,
            detail="Falha ao gerar o PDF do relatório.",
        )

    return HTMLResponse(content=html_content)
