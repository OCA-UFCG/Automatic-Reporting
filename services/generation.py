import logging
import re
import unicodedata
from datetime import datetime

from fastapi import HTTPException
from fastapi.responses import HTMLResponse

from config import (
    CARACTERISTICAS_DOCS_URL,
    OUTPUT_DIR,
)
from plotting.demografia import (
    gerar_grafico_composicao_cor_raca,
    gerar_grafico_faixa_etaria_e_sexo,
    gerar_grafico_visao_historica_populacao,
)
from plotting.desenvolvimento_social import gerar_grafico_de_desenvolvimento_social
from plotting.economia_renda import (
    gerar_grafico_balanca,
    gerar_grafico_exportacao,
    gerar_grafico_fob,
    gerar_grafico_pib,
    gerar_grafico_vab,
)
from plotting.educacao import gerar_grafico_cor_faixa_etaria
from plotting.hidraulica import gerar_grafico_tecnologias_acesso_agua
from plotting.meio_ambiente import gerar_grafico_aridez
from plotting.saneamento import gerar_grafico_esgotamento_sanitario
from plotting.saude import (
    gerar_grafico_cobertura_vacinal,
    gerar_grafico_de_estabelecimento,
    gerar_grafico_mortalidade_infantil,
    gerar_grafico_publico_etario,
)
from services.contexto import CacheDeEnriquecimento, montar_linhas_macrotema
from services.macrotemas import get_macrotema, get_macrotema_slugs_para_relatorio
from services.pdf import _gerar_pdf
from utils.cover import (
    montar_capa_relatorio,
    montar_indicadores_macrotema,
    montar_score_macrotema,
)
from utils.data.macrotemas import TODOS_MACROTEMAS_SLUG
from utils.external.docs import (
    carregar_texto_do_docs,
    extrair_descricao_tema,
    extrair_diagnostico_cidade,
    extrair_inicio_relatorio,
    extrair_introducao,
    extrair_legenda_mapa_localizacao,
    extrair_referencias,
    extrair_relatorio_geral,
    extrair_resumo_cidade,
    extrair_resumo_relatorio,
    extrair_resumo_tema,
    remover_titulos_docs,
)
from utils.external.editorial import (
    ContratoIndisponivel,
    carregar_texto_editorial,
    fonte_editorial,
)
from utils.render.renderer import (
    render_descricao_tema_html,
    render_mapa_marker,
    reset_figura_contador,
    resolver_referencia_figura_do_mapa,
    substituir_placeholders,
    texto_para_html,
)
from utils.ssr import render_react_ssr

logger = logging.getLogger(__name__)

GRAFICOS_AUTO_MARCADOR = {
    "demografia": (
        (
            "grafico_faixa_etaria_e_sexo",
            (
                r"(?im)^(\s*Figura\s+[A-Za-z0-9&]+\s*[-–]\s*"
                r"Popula[cç][aã]o\s+por\s+faixa\s+et[aá]ria\s+e\s+sexo[^\n]*)$"
            ),
        ),
        (
            "grafico_composicao_cor_raca",
            (
                r"(?im)^(\s*Figura\s+[A-Za-z0-9&]+\s*[-–]\s*"
                r"Composi[cç][aã]o\s+por\s+cor\s+ou\s+ra[cç]a[^\n]*)$"
            ),
        ),
        (
            "grafico_visao_historica",
            (
                r"(?im)^(\s*Figura\s+[A-Za-z0-9&]+\s*[-–]\s*"
                r"Vis[aã]o\s+hist[oó]rica\s+da\s+popula[cç][aã]o[^\n]*)$"
            ),
        ),
    ),
    "saude": (
        (
            "grafico_cobertura_vacinal",
            (
                r"(?im)^(\s*Figura\s+[A-Za-z0-9&]+\s*[-–]\s*"
                r"Taxa\s+de\s+cobertura\s+vacinal\s+por\s+tipo\s+de\s+vacina[^\n]*)$"
            ),
        ),
        (
            "grafico_mortalidade_infantil",
            (
                r"(?im)^(\s*Figura\s+[A-Za-z0-9&]+\s*[-–]\s*"
                r"Vis[aã]o\s+hist[oó]rica\s+da\s+taxa\s+de\s+mortalidade\s+infantil[^\n]*)$"
            ),
        ),
        (
            "grafico_de_estabelecimento",
            (
                r"(?im)^(\s*Figura\s+[A-Za-z0-9&]+\s*[-–]\s*"
                r"Vis[aã]o\s+hist[oó]rica\s+do\s+n[uú]mero\s+de\s+"
                r"estabelecimentos\s+de\s+sa[uú]de[^\n]*)$"
            ),
        ),
    ),
    "economia-renda": (
        (
            "grafico_pib",
            (
                r"(?im)^(\s*Figura\s+[A-Za-z0-9&]+\s*[-–]\s*"
                r"Evolu[cç][aã]o\s+anual\s+do\s+PIB\s+total[^\n]*)$"
            ),
        ),
        (
            "grafico_vab",
            (
                r"(?im)^(\s*Figura\s+[A-Za-z0-9&]+\s*[-–]\s*"
                r"Valor\s+Adicionado\s+Bruto\s*\(VAB\)\s+por\s+setor[^\n]*)$"
            ),
        ),
        (
            "grafico_fob",
            (
                r"(?im)^(\s*Figura\s+[A-Za-z0-9&]+\s*[-–]\s*"
                r"Destinos\s+das\s+importa[cç][oõ]es\s+ordenados\s+pelo\s+"
                r"valor\s+l[ií]quido\s+FOB[^\n]*)$"
            ),
        ),
        (
            "grafico_exportacao",
            (
                r"(?im)^(\s*Figura\s+[A-Za-z0-9&]+\s*[-–]\s*"
                r"Destinos\s+das\s+exporta[cç][oõ]es\s+ordenados\s+pelo\s+"
                r"valor\s+l[ií]quido\s+FOB[^\n]*)$"
            ),
        ),
        (
            "grafico_balanca",
            (
                r"(?im)^(\s*Figura\s+[A-Za-z0-9&]+\s*[-–]\s*"
                r"Vis[aã]o\s+mensal\s+da\s+balan[cç]a\s+comercial[^\n]*)$"
            ),
        ),
    ),
    "saneamento": (
        (
            "grafico_esgotamento_sanitario",
            (
                r"(?im)^(\s*Figura\s+[A-Za-z0-9&]+\s*[-–]\s*"
                r"Domic[ií]lios\s+por\s+tipo\s+de\s+esgotamento\s+sanit[aá]rio[^\n]*)$"
            ),
        ),
    ),
    "meio-ambiente": (
        (
            "grafico_aridez",
            (
                r"(?im)^(\s*Figura\s+[A-Za-z0-9&]+\s*[-–]\s*"
                r"Classifica[cç][aã]o\s+das\s+condi[cç][oõ]es\s+de\s+aridez[^\n]*)$"
            ),
        ),
    ),
}


async def gerar_relatorio_handler(
    cidade: str,
    macrotema: str = "demografia",
    *,
    prefixo_artefato: str = "",
    gerar_pdf: bool = True,
):
    """Gera o relatório do município.

    ``prefixo_artefato`` separa os arquivos de saída dos de produção. A prévia
    do painel roda este mesmo pipeline com um contrato ainda não publicado; sem
    o prefixo ela sobrescreveria `output/relatorio_<tema>__<cidade>.pdf`, que é
    o arquivo que o portal entrega ao público — prosa não publicada iria ao ar
    pela porta dos fundos.

    ``gerar_pdf=False`` devolve só o HTML. É o que a prévia quer: o PDF sai
    desse mesmo HTML pelo WeasyPrint, então o conteúdo é o mesmo e o editor não
    precisa esperar a conversão.
    """
    reset_figura_contador()
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

    # As consultas de enriquecimento valem para o relatório inteiro; o cache
    # evita repeti-las a cada macrotema do laço.
    cache_enriquecimento = CacheDeEnriquecimento()

    for macrotema_slug in macrotema_slugs:
        try:
            macrotema_dados = get_macrotema(macrotema_slug)
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))

        # Um macrotema servido pelo painel não precisa de Doc configurado — a
        # prosa vem do contrato publicado.
        if not macrotema_dados["docs_url"] and fonte_editorial(macrotema_slug) == "docs":
            logger.warning(
                "Macrotema '%s' não possui docs_url configurado (%s). Pulando.",
                macrotema_slug,
                macrotema_dados["docs_env"],
            )
            continue
        linhas_macrotema, _origem = montar_linhas_macrotema(
            macrotema_slug,
            macrotema_dados,
            cidade,
            gerado_em,
            macrotema_slugs,
            cache_enriquecimento,
        )

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
            safe_report = f"{prefixo_artefato}{slug_arquivo}__{safe_city}"

            legenda_mapa_localizacao = None
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
                legenda_mapa_localizacao, caracteristicas_texto = (
                    extrair_legenda_mapa_localizacao(caracteristicas_texto)
                )
                if legenda_mapa_localizacao:
                    legenda_mapa_localizacao = substituir_placeholders(
                        legenda_mapa_localizacao,
                        contexto_caracteristicas,
                        "caract_mun",
                    )
                    if resumo_cidade:
                        resumo_cidade = resolver_referencia_figura_do_mapa(
                            resumo_cidade
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

        eh_primeiro = macrotema_slug == macrotema_slugs[0]

        graficos_por_placeholder = {}

        if macrotema_slug == "demografia":
            for nome_grafico, gerar_grafico in (
                ("grafico_faixa_etaria_e_sexo", gerar_grafico_faixa_etaria_e_sexo),
                ("grafico_composicao_cor_raca", gerar_grafico_composicao_cor_raca),
                ("grafico_visao_historica", gerar_grafico_visao_historica_populacao),
            ):
                try:
                    graficos_por_placeholder[nome_grafico] = gerar_grafico(
                        cidade=linhas_macrotema[0],
                        OUTPUT_DIR=OUTPUT_DIR,
                        safe_city=safe_report or "relatorio",
                    )
                except ValueError as err:
                    logger.warning(
                        "Não foi possível gerar o gráfico '%s' para '%s': %s",
                        nome_grafico,
                        safe_report,
                        err,
                    )

        if macrotema_slug == "educacao":
            try:
                chart_file_name = gerar_grafico_cor_faixa_etaria(
                    cidade=linhas_macrotema[0],
                    OUTPUT_DIR=OUTPUT_DIR,
                    safe_city=safe_city or "relatorio",
                )
                graficos_por_placeholder["grafico_cor_faixa_etaria"] = chart_file_name
            except ValueError as err:
                logger.warning(
                    "Não foi possível gerar o gráfico de cor/faixa etária de "
                    "educação para '%s': %s",
                    safe_report,
                    err,
                )

        if macrotema_slug == "saude":
            for nome_grafico, gerar_grafico in (
                ("grafico_publico_etario", gerar_grafico_publico_etario),
                ("grafico_cobertura_vacinal", gerar_grafico_cobertura_vacinal),
                ("grafico_mortalidade_infantil", gerar_grafico_mortalidade_infantil),
                ("grafico_de_estabelecimento", gerar_grafico_de_estabelecimento),
            ):
                try:
                    graficos_por_placeholder[nome_grafico] = gerar_grafico(
                        cidade=linhas_macrotema[0],
                        OUTPUT_DIR=OUTPUT_DIR,
                        safe_city=safe_city or "relatorio",
                    )
                except (ValueError, KeyError) as err:
                    logger.warning(
                        "Não foi possível gerar o gráfico '%s' para '%s': %s",
                        nome_grafico,
                        safe_report,
                        err,
                    )

        if macrotema_slug == "hidraulica":
            try:
                chart_file_name = gerar_grafico_tecnologias_acesso_agua(
                    cidade=linhas_macrotema[0],
                    OUTPUT_DIR=OUTPUT_DIR,
                    safe_city=safe_report or "relatorio",
                )
                graficos_por_placeholder["grafico_tecnologias_acesso_agua"] = (
                    chart_file_name
                )
            except ValueError as err:
                logger.warning(
                    "Não foi possível gerar o gráfico de tecnologias de acesso "
                    "à água para '%s': %s",
                    safe_report,
                    err,
                )

        if macrotema_slug == "meio-ambiente":
            try:
                graficos_por_placeholder["grafico_aridez"] = gerar_grafico_aridez(
                    cidade=linhas_macrotema[0],
                    OUTPUT_DIR=OUTPUT_DIR,
                    safe_city=safe_report or "relatorio",
                )
            except ValueError as err:
                logger.warning(
                    "Não foi possível gerar o gráfico de classificação de "
                    "aridez para '%s': %s",
                    safe_report,
                    err,
                )

        if macrotema_slug == "saneamento":
            try:
                graficos_por_placeholder["grafico_esgotamento_sanitario"] = (
                    gerar_grafico_esgotamento_sanitario(
                        cidade=linhas_macrotema[0],
                        OUTPUT_DIR=OUTPUT_DIR,
                        safe_city=safe_report or "relatorio",
                    )
                )
            except (ValueError, KeyError) as err:
                logger.warning(
                    "Não foi possível gerar o gráfico de esgotamento sanitário "
                    "para '%s': %s",
                    safe_report,
                    err,
                )

        if macrotema_slug == "desenvolvimento-social":
            try:
                chart_file_name = gerar_grafico_de_desenvolvimento_social(
                    cidade=linhas_macrotema[0],
                    OUTPUT_DIR=OUTPUT_DIR,
                    safe_city=safe_report or "relatorio",
                )
                graficos_por_placeholder["grafico_de_desenvolvimento_social"] = (
                    chart_file_name
                )
            except ValueError as err:
                logger.warning(
                    "Não foi possível gerar o gráfico de desenvolvimento social "
                    "para '%s': %s",
                    safe_report,
                    err,
                )

        if macrotema_slug == "economia-renda":
            try:
                chart_file_name = gerar_grafico_pib(
                    cidade=linhas_macrotema[0],
                    OUTPUT_DIR=OUTPUT_DIR,
                    safe_city=safe_report or "relatorio",
                )
                graficos_por_placeholder["grafico_pib"] = chart_file_name
            except ValueError as err:
                logger.warning(
                    "Não foi possível gerar o gráfico de evolução do PIB "
                    "para '%s': %s",
                    safe_report,
                    err,
                )

            try:
                chart_file_name = gerar_grafico_vab(
                    cidade=linhas_macrotema[0],
                    OUTPUT_DIR=OUTPUT_DIR,
                    safe_city=safe_report or "relatorio",
                )
                graficos_por_placeholder["grafico_vab"] = chart_file_name
            except ValueError as err:
                logger.warning(
                    "Não foi possível gerar o gráfico de VAB por setor "
                    "para '%s': %s",
                    safe_report,
                    err,
                )

            try:
                chart_file_name = gerar_grafico_fob(
                    cidade=linhas_macrotema[0],
                    OUTPUT_DIR=OUTPUT_DIR,
                    safe_city=safe_report or "relatorio",
                )
                graficos_por_placeholder["grafico_fob"] = chart_file_name
            except ValueError as err:
                logger.warning(
                    "Não foi possível gerar o gráfico de países de importação "
                    "para '%s': %s",
                    safe_report,
                    err,
                )

            try:
                chart_file_name = gerar_grafico_exportacao(
                    cidade=linhas_macrotema[0],
                    OUTPUT_DIR=OUTPUT_DIR,
                    safe_city=safe_report or "relatorio",
                )
                graficos_por_placeholder["grafico_exportacao"] = chart_file_name
            except ValueError as err:
                logger.warning(
                    "Não foi possível gerar o gráfico de países de exportação "
                    "para '%s': %s",
                    safe_report,
                    err,
                )

            try:
                chart_file_name = gerar_grafico_balanca(
                    cidade=linhas_macrotema[0],
                    OUTPUT_DIR=OUTPUT_DIR,
                    safe_city=safe_report or "relatorio",
                )
                graficos_por_placeholder["grafico_balanca"] = chart_file_name
            except ValueError as err:
                logger.warning(
                    "Não foi possível gerar o gráfico de balança comercial "
                    "para '%s': %s",
                    safe_report,
                    err,
                )

        # Único ponto de entrada da prosa do macrotema. É o seam entre o Google
        # Doc e o painel editorial: quem decide a fonte é FONTE_EDITORIAL, por
        # macrotema (docs/PLANO-PAINEL-EDITORIAL.md §3.1). Daqui para baixo o
        # texto é o mesmo nos dois caminhos.
        try:
            docs_texto = await carregar_texto_editorial(
                macrotema_slug, macrotema_dados, linhas_macrotema[0]
            )
        except ContratoIndisponivel as err:
            raise HTTPException(status_code=500, detail=str(err)) from err
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err)) from err

        for nome_grafico, legenda_regex in GRAFICOS_AUTO_MARCADOR.get(macrotema_slug, ()):
            if re.search(rf"(?m)^\s*(?:%%|\*){nome_grafico}\s*$", docs_texto):
                continue
            docs_texto, n_substituicoes = re.subn(
                legenda_regex,
                f"*{nome_grafico}\n\n\\1",
                docs_texto,
                count=1,
            )
            if not n_substituicoes:
                logger.warning(
                    "Não foi possível localizar a legenda para inserir o "
                    "marcador do gráfico '%s' no documento de '%s'. O "
                    "gráfico foi gerado mas não será exibido no relatório.",
                    nome_grafico,
                    safe_report,
                )

        macrotema_item: dict[str, object] = {
            "nome": macrotema_dados["nome"],
            "slug": macrotema_slug,
            "icone": macrotema_dados["icone"],
            "cor": macrotema_dados["cor"],
            "resumo": "",
            "descricao": "",
            "descricao_paragrafos": [],
            "descricao_html": [],
            "fontes_html": "",
            "score": montar_score_macrotema(linhas_macrotema[0]),
            "indicadores": montar_indicadores_macrotema(
                macrotema_slug, linhas_macrotema[0], macrotema_dados["icone"]
            ),
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
                linhas_macrotema[0], safe_report, legenda=legenda_mapa_localizacao
            )

        # O que sobra do Doc após extrair descricao_tema/resumo/etc. é a caixa
        # "Fontes"/"Conteúdos relacionados" (com "Continue explorando o tema")
        # daquele macrotema. Fica presa à própria página do tema — não some
        # num blob global — para fechar o tema antes do próximo começar.
        macrotema_item["fontes_html"] = texto_para_html(
            docs_texto,
            linhas_macrotema[0],
            namespace=macrotema_slug,
            graficos_por_placeholder=graficos_por_placeholder,
            safe_report=safe_report,
        )

        macrotemas_render.append(macrotema_item)

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

    if gerar_pdf and not await _gerar_pdf(html_content, pdf_file):
        raise HTTPException(
            status_code=500,
            detail="Falha ao gerar o PDF do relatório.",
        )

    return HTMLResponse(content=html_content)
