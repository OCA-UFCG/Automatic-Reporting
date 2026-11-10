"""Relatório de um estado: o mesmo produto do relatório municipal, com a linha do
estado na matview estadual do tema e o Doc estadual do tema.

Pedido de 05/11/2026: a busca do portal (data-nordeste-frontend) passa a achar os 9
estados do Nordeste ao lado dos municípios. Um handler à parte, e não um `unidade`
costurado em gerar_relatorio_handler, para não arriscar o relatório municipal: o
estado divide com ele só o gate de cache, a fila de geração, o SSR e o PDF
(responder_sem_gerar e gravar_relatorio em services/generation.py).

Fica de fora por enquanto, como no Laboratório com unidade=estado:
  - gráficos: GRAFICOS_POR_TEMA lê colunas municipais; a menção "(Figura X)" do Doc
    some como num gráfico sem dado;
  - mapa de localização, Características Gerais e os cards de indicadores da capa:
    todos leem o município (vw_indicadores, shapefile por município).
"""

import logging
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
from utils.cover import montar_capa_relatorio
from utils.data.estados import resolver_estado
from utils.data.macrotemas import TODOS_MACROTEMAS_ORDEM
from utils.external.docs import carregar_texto_do_docs
from utils.queries.estado import buscar_contexto_estado
from utils.render.placeholders import substituir_placeholders
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
class TemaDoEstado:
    """Um tema pronto para o SSR: o item de `cover.macrotemas`, o contexto que
    resolveu os placeholders e o Doc fatiado (a capa e as Referências leem dele)."""

    item: dict[str, object]
    contexto: dict
    secoes: SecoesTema


def nome_do_estado_ou_404(estado: str) -> str:
    """Nome canônico do estado pedido, ou 404 com o nome recebido."""
    estado_canonico = resolver_estado(estado)
    if estado_canonico is None:
        raise HTTPException(status_code=404, detail=f"Estado '{estado}' não encontrado.")
    return estado_canonico


def slugs_em_ordem_ou_400(macrotema: str) -> list[str]:
    """Os temas pedidos na ordem canônica do relatório (a mesma de
    gerar_relatorio_handler, que é o que torna a chave de cache verdadeira)."""
    try:
        slugs = get_macrotema_slugs_para_relatorio(macrotema)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    return sorted(slugs, key=TODOS_MACROTEMAS_ORDEM.index)


async def gerar_relatorio_estado_handler(
    estado: str,
    macrotema: str = "demografia",
    aguardar: bool = True,
    _sentinela_ja_adquirida: bool = False,
) -> HTMLResponse:
    """Relatório do estado nos temas pedidos, com o mesmo contrato HTTP do municipal
    (cache, 202 com aguardar=False, headers do artefato).

    Ex.: `await gerar_relatorio_estado_handler("Paraíba", "demografia,saude")`
    """
    invalidar_query_cache_se_dados_mudaram()
    estado_canonico = nome_do_estado_ou_404(estado)
    slugs = slugs_em_ordem_ou_400(macrotema)
    _, safe_report = montar_safe_report(estado_canonico, macrotema, slugs)
    resposta_sem_gerar = responder_sem_gerar(
        safe_report,
        aguardar,
        lambda: gerar_relatorio_estado_handler(
            estado_canonico, macrotema, aguardar=True, _sentinela_ja_adquirida=True
        ),
    )
    if resposta_sem_gerar is not None:
        return resposta_sem_gerar

    dono_da_sentinela = False if _sentinela_ja_adquirida else adquirir_geracao(safe_report)
    try:
        return await _gerar(estado_canonico, slugs, safe_report)
    finally:
        if dono_da_sentinela:
            liberar_geracao(safe_report)


async def _gerar(estado: str, slugs: list[str], safe_report: str) -> HTMLResponse:
    # Escopo de render, como no municipal: o contador de figuras vive num ContextVar.
    reset_figura_contador()
    # Fuso fixo: o container roda em UTC (ver gerar_relatorio_handler).
    gerado_em = datetime.now(ZoneInfo("America/Fortaleza"))
    temas = [
        tema
        for slug in slugs
        if (tema := await tema_do_estado(slug, estado, gerado_em, safe_report)) is not None
    ]
    # Sem nenhum tema, o PDF sairia só com a capa e ficaria no cache pelo TTL. Melhor
    # um erro honesto: quase sempre é o banco fora do ar ou um Doc não configurado.
    if not temas:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Sem dados do estado '{estado}' para '{','.join(slugs)}': "
                "esperava a linha na matview estadual e o <TEMA>_ESTADO_DOCS_URL configurado."
            ),
        )
    referencias = [ref for tema in temas for ref in tema.secoes.referencias]
    html_content = await render_react_ssr({
        "cover": capa_do_estado(estado, temas, gerado_em, safe_report),
        "docsHtml": html_das_referencias(referencias, safe_report) or "",
        "dados": [temas[0].contexto],
    })
    return await gravar_relatorio(html_content, safe_report)


async def tema_do_estado(
    slug: str, estado: str, gerado_em: datetime, safe_report: str
) -> TemaDoEstado | None:
    """O tema pronto para o SSR, ou None (com aviso no log) quando falta o Doc
    estadual ou a linha do estado na matview: o tema some do relatório, como um
    tema sem Doc no municipal."""
    url_do_doc = docs_url(slug, "estado")
    if not url_do_doc:
        logger.warning("Relatório de %s: tema '%s' sem Doc estadual configurado. Pulando.", estado, slug)
        return None
    linha = buscar_contexto_estado(slug, estado)
    if linha is None:
        logger.warning("Relatório de %s: tema '%s' sem linha na matview estadual. Pulando.", estado, slug)
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
    secoes, _ = separar_secoes_do_tema(texto_do_doc, slug)
    return TemaDoEstado(item_do_tema(slug, secoes, contexto, safe_report), contexto, secoes)


def item_do_tema(slug: str, secoes: SecoesTema, contexto: dict, safe_report: str) -> dict[str, object]:
    """O item de `cover.macrotemas` com as mesmas chaves do municipal. Sem gráficos
    (`graficos_por_placeholder={}`) e sem cards de indicadores, que leem o município."""
    dados_do_tema = get_macrotema(slug)
    descricao = secoes.descricao_tema or ""
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
            secoes.resto, contexto, namespace=slug, graficos_por_placeholder={}, safe_report=safe_report
        ),
        "score": None,
        "indicadores": [],
    }


def capa_do_estado(
    estado: str, temas: list[TemaDoEstado], gerado_em: datetime, safe_report: str
) -> dict[str, object]:
    """A capa: título com o estado e a sigla, tags dos temas e os blocos de capa do
    Doc do primeiro tema. `unidade` diz ao SSR para trocar "Dados municipais" por
    "Dados estaduais" (report/src/components/Report.jsx)."""
    primeiro = temas[0]
    cover = montar_capa_relatorio(primeiro.contexto, gerado_em, primeiro.item["nome"], primeiro.item["slug"])
    cover.update({
        "unidade": "estado",
        "cidade_nome": estado,
        "uf": str(primeiro.contexto.get("uf_sigla_uf") or ""),
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
