"""Relatório de uma unidade além do município (estado ou área de interesse): o mesmo produto do
relatório municipal, com a linha da unidade na matview do tema e o Doc do tema na
unidade.

Uma unidade nova entra em UNIDADES_DO_RELATORIO com o jeito de achar o nome e a linha
dela, sem um handler novo (assim entrou a área de interesse, em 12/11/2026).

Pedido de 05/11/2026: a busca do portal (data-nordeste-frontend) passa a achar os 9
estados do Nordeste ao lado dos municípios. Um handler à parte, e não um `unidade`
costurado em gerar_relatorio_handler, para não arriscar o relatório municipal: o
estado divide com ele só o gate de cache, a fila de geração, o SSR e o PDF
(responder_sem_gerar e gravar_relatorio em services/generation.py).

Fica de fora por enquanto, como no Laboratório com unidade=estado:
  - gráficos: GRAFICOS_POR_TEMA lê colunas municipais; a menção "(Figura X)" do Doc
    some como num gráfico sem dado;
  - mapa de localização e Características Gerais: leem o município (shapefile por
    município, vw_indicadores).

Os cards do tema ("Panorama de indicadores") vêm do próprio Doc estadual desde
11/11/2026: pares rótulo / `$campo` resolvidos contra a linha da matview
(montar_indicadores_do_doc em utils/cover.py).
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from fastapi.responses import HTMLResponse

from services.cache import (
    adquirir_geracao,
    invalidar_query_cache_se_dados_mudaram,
    liberar_geracao,
)
from services.generation import (
    SecoesTema,
    gravar_relatorio,
    html_das_referencias,
    montar_safe_report,
    paragrafos_com_valores,
    responder_sem_gerar,
    separar_secoes_do_tema,
)
from services.macrotemas import (
    docs_url,
    get_macrotema,
    get_macrotema_slugs_para_relatorio,
)
from utils.cover import montar_capa_relatorio, montar_indicadores_do_doc
from utils.data.areas import resolver_area
from utils.data.estados import resolver_estado
from utils.data.macrotemas import TODOS_MACROTEMAS_ORDEM
from utils.external.docs import carregar_texto_do_docs, extrair_panorama_indicadores
from utils.queries.area import buscar_contexto_area
from utils.queries.estado import buscar_contexto_estado
from utils.render.placeholders import (
    isolar_paragrafo_de_cada_condicao,
    substituir_placeholders,
)
from utils.render.renderer import (
    render_descricao_tema_html,
    reset_figura_contador,
    texto_para_html,
)
from utils.ssr import render_react_ssr

logger = logging.getLogger(__name__)

# Os blocos do Doc do primeiro tema que o relatório municipal leva para a capa
# (generation.py, `eh_primeiro`). No Doc estadual, `resumo_cidade` é o resumo do estado:
# o nome do bloco é o do template, compartilhado com o Doc municipal.
_BLOCOS_DA_CAPA = ("relatorio_geral", "resumo_cidade", "diagnostico_cidade")


@dataclass(frozen=True)
class UnidadeDoRelatorio:
    """O que muda de uma unidade para outra; o resto do handler é comum.

    `nao_encontrado` é a mensagem do 404, com `{}` no lugar do nome. `buscar` recebe (slug, nome canônico) e devolve a linha da matview do tema, ou
    None. `coluna_sigla` é a coluna que vai ao lado do nome no título da capa
    ("Paraíba - PB"); None quando a unidade não tem sigla.
    """

    nao_encontrado: str
    resolver: Callable[[str], str | None]
    buscar: Callable[[str, str], dict | None]
    coluna_sigla: str | None


UNIDADES_DO_RELATORIO: dict[str, UnidadeDoRelatorio] = {
    # `buscar` chama buscar_contexto_estado pelo nome do módulo na hora, e não guarda a
    # função: os testes trocam essa costura com monkeypatch. O mesmo vale para a área.
    "estado": UnidadeDoRelatorio(
        nao_encontrado="Estado '{}' não encontrado.",
        resolver=resolver_estado,
        buscar=lambda slug, nome: buscar_contexto_estado(slug, nome),
        coluna_sigla="uf_sigla_uf",
    ),
    # Área de interesse (12/11/2026): sem sigla; o título da capa é só o nome.
    "area": UnidadeDoRelatorio(
        nao_encontrado="Área de interesse '{}' não encontrada.",
        resolver=resolver_area,
        buscar=lambda slug, nome: buscar_contexto_area(slug, nome),
        coluna_sigla=None,
    ),
}


@dataclass(frozen=True)
class TemaDoEstado:
    """Um tema pronto para o SSR: o item de `cover.macrotemas`, o contexto que
    resolveu os placeholders e o Doc fatiado (a capa e as Referências leem dele)."""

    item: dict[str, object]
    contexto: dict
    secoes: SecoesTema


def nome_da_unidade_ou_404(unidade: str, nome: str) -> str:
    """Nome canônico da unidade pedida, ou 404 com o nome recebido."""
    config = UNIDADES_DO_RELATORIO[unidade]
    nome_canonico = config.resolver(nome)
    if nome_canonico is None:
        raise HTTPException(status_code=404, detail=config.nao_encontrado.format(nome))
    return nome_canonico


def slugs_em_ordem_ou_400(macrotema: str) -> list[str]:
    """Os temas pedidos na ordem canônica do relatório (a mesma de
    gerar_relatorio_handler, que é o que torna a chave de cache verdadeira)."""
    try:
        slugs = get_macrotema_slugs_para_relatorio(macrotema)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    return sorted(slugs, key=TODOS_MACROTEMAS_ORDEM.index)


async def gerar_relatorio_estado_handler(
    estado: str, macrotema: str = "demografia", aguardar: bool = True
) -> HTMLResponse:
    """Relatório do estado. Ex.: `await gerar_relatorio_estado_handler("Paraíba", "demografia,saude")`"""
    return await gerar_relatorio_unidade_handler("estado", estado, macrotema, aguardar)


async def gerar_relatorio_unidade_handler(
    unidade: str,
    nome: str,
    macrotema: str = "demografia",
    aguardar: bool = True,
    _sentinela_ja_adquirida: bool = False,
) -> HTMLResponse:
    """Relatório da unidade nos temas pedidos, com o mesmo contrato HTTP do municipal
    (cache, 202 com aguardar=False, headers do artefato).

    Ex.: `await gerar_relatorio_unidade_handler("estado", "Paraíba", "demografia,saude")`
    """
    invalidar_query_cache_se_dados_mudaram()
    nome_canonico = nome_da_unidade_ou_404(unidade, nome)
    slugs = slugs_em_ordem_ou_400(macrotema)
    _, safe_report = montar_safe_report(nome_canonico, macrotema, slugs)
    resposta_sem_gerar = responder_sem_gerar(
        safe_report,
        aguardar,
        lambda: gerar_relatorio_unidade_handler(
            unidade, nome_canonico, macrotema, aguardar=True, _sentinela_ja_adquirida=True
        ),
    )
    if resposta_sem_gerar is not None:
        return resposta_sem_gerar

    dono_da_sentinela = False if _sentinela_ja_adquirida else adquirir_geracao(safe_report)
    try:
        return await _gerar(unidade, nome_canonico, slugs, safe_report)
    finally:
        if dono_da_sentinela:
            liberar_geracao(safe_report)


async def _gerar(unidade: str, nome: str, slugs: list[str], safe_report: str) -> HTMLResponse:
    # Escopo de render, como no municipal: o contador de figuras vive num ContextVar.
    reset_figura_contador()
    # Fuso fixo: o container roda em UTC (ver gerar_relatorio_handler).
    gerado_em = datetime.now(ZoneInfo("America/Fortaleza"))
    temas = [
        tema
        for slug in slugs
        if (tema := await tema_da_unidade(unidade, slug, nome, gerado_em, safe_report)) is not None
    ]
    # Sem nenhum tema, o PDF sairia só com a capa e ficaria no cache pelo TTL. Melhor
    # um erro honesto: quase sempre é o banco fora do ar ou um Doc não configurado.
    if not temas:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Sem dados de '{nome}' para '{','.join(slugs)}': esperava a linha na "
                f"matview do tema e o <TEMA>_{unidade.upper()}_DOCS_URL configurado."
            ),
        )
    referencias = [ref for tema in temas for ref in tema.secoes.referencias]
    html_content = await render_react_ssr({
        "cover": capa_da_unidade(unidade, nome, temas, gerado_em, safe_report),
        "docsHtml": html_das_referencias(referencias, safe_report) or "",
        "dados": [temas[0].contexto],
    })
    return await gravar_relatorio(html_content, safe_report)


async def tema_da_unidade(
    unidade: str, slug: str, nome: str, gerado_em: datetime, safe_report: str
) -> TemaDoEstado | None:
    """O tema pronto para o SSR, ou None (com aviso no log) quando falta o Doc do
    tema na unidade ou a linha da unidade na matview: o tema some do relatório, como
    um tema sem Doc no municipal."""
    url_do_doc = docs_url(slug, unidade)
    if not url_do_doc:
        logger.warning("Relatório de %s: tema '%s' sem Doc de %s configurado. Pulando.", nome, slug, unidade)
        return None
    linha = UNIDADES_DO_RELATORIO[unidade].buscar(slug, nome)
    if linha is None:
        logger.warning("Relatório de %s: tema '%s' sem linha na matview de %s. Pulando.", nome, slug, unidade)
        return None
    contexto = {
        **linha,
        "data_relatorio": gerado_em.strftime("%d/%m/%Y"),
        "hora_relatorio": gerado_em.strftime("%H:%M"),
    }
    try:
        texto_do_doc = await carregar_texto_do_docs(url_do_doc)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    # No Doc estadual cada condição vale só para a linha seguinte (ver
    # isolar_paragrafo_de_cada_condicao), e o mesmo vale para as outras unidades; o
    # Laboratório faz o mesmo com unidade=estado.
    secoes, _ = separar_secoes_do_tema(isolar_paragrafo_de_cada_condicao(texto_do_doc), slug)
    return TemaDoEstado(item_do_tema(slug, secoes, contexto, safe_report), contexto, secoes)


def item_do_tema(slug: str, secoes: SecoesTema, contexto: dict, safe_report: str) -> dict[str, object]:
    """O item de `cover.macrotemas` com as mesmas chaves do municipal. Sem gráficos
    (`graficos_por_placeholder={}`); os cards de indicadores vêm do bloco "Panorama
    de indicadores" do Doc, que sai do resto para não ir parar na caixa de Fontes."""
    dados_do_tema = get_macrotema(slug)
    descricao = secoes.descricao_tema or ""
    panorama, resto = extrair_panorama_indicadores(secoes.resto)
    return {
        "nome": dados_do_tema["nome"],
        "slug": slug,
        "icone": dados_do_tema["icone"],
        "cor": dados_do_tema["cor"],
        "resumo": substituir_placeholders(secoes.resumo_tema, contexto, slug) if secoes.resumo_tema else "",
        "descricao": substituir_placeholders(descricao, contexto, slug),
        "descricao_paragrafos": paragrafos_com_valores(descricao, contexto, slug),
        "descricao_html": render_descricao_tema_html(
            descricao, contexto, namespace=slug, safe_report=safe_report, graficos_por_placeholder={}
        ) if descricao else [],
        "fontes_html": texto_para_html(
            resto, contexto, namespace=slug, graficos_por_placeholder={}, safe_report=safe_report
        ),
        "score": None,
        "indicadores": montar_indicadores_do_doc(panorama, contexto, slug, dados_do_tema["icone"]),
    }


def capa_da_unidade(
    unidade: str, nome: str, temas: list[TemaDoEstado], gerado_em: datetime, safe_report: str
) -> dict[str, object]:
    """A capa: título com o nome e a sigla, tags dos temas e os blocos de capa do Doc
    do primeiro tema. `unidade` diz ao SSR para trocar "Dados municipais" pelo rótulo
    da unidade (report/src/components/rotuloDaUnidade.js)."""
    primeiro = temas[0]
    coluna_sigla = UNIDADES_DO_RELATORIO[unidade].coluna_sigla
    cover = montar_capa_relatorio(primeiro.contexto, gerado_em, primeiro.item["nome"], primeiro.item["slug"])
    cover.update({
        "unidade": unidade,
        "cidade_nome": nome,
        "uf": str(primeiro.contexto.get(coluna_sigla) or "") if coluna_sigla else "",
        # Área e população vêm da vw_indicadores municipal: no estado sairiam "N/D".
        "metricas": [],
        "macrotemas": [tema.item for tema in temas],
        "macrotemas_tags": [
            {"nome": tema.item["nome"], "slug": tema.item["slug"], "cor": tema.item["cor"]} for tema in temas
        ],
    })
    for campo in ("resumo", "descricao", "descricao_paragrafos", "descricao_html"):
        cover["macrotema"][campo] = primeiro.item[campo]
    for bloco in _BLOCOS_DA_CAPA:
        texto = getattr(primeiro.secoes, bloco)
        if not texto:
            continue
        cover[bloco] = substituir_placeholders(texto, primeiro.contexto, primeiro.item["slug"])
        cover[f"{bloco}_html"] = render_descricao_tema_html(
            texto, primeiro.contexto, namespace=primeiro.item["slug"], safe_report=safe_report
        )
    return cover
