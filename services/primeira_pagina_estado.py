"""Primeira página do relatório por estado (13/11/2026): Apresentação, os cards de área e
população e Características Gerais, lidos de um Doc próprio
(CARACTERISTICAS_ESTADO_DOCS_URL) contra a linha do estado em est_caract_mun.

É o equivalente estadual do Doc de Características Gerais do município
(CARACTERISTICAS_DOCS_URL em services/generation.py), com os mesmos blocos marcados:
`apresentacao = “…” @@` e `resumo_cidade = “…” @@`. Os campos do Doc usam o prefixo
`geral.` (ex.: `geral.$uf_de`). Os cards vêm do bloco "Panorama de indicadores", no
mesmo formato dos Docs de tema.

Sem a variável configurada ou sem a linha do estado, a capa fica como antes: os blocos
de capa do Doc do primeiro tema (services/relatorio_estado.py, capa_da_unidade).

Mapa de localização desde 17/11/2026, só no modo congelado (beta): um PNG por unidade na
pasta congelada, que vira a Figura 1. Sem mapa, a menção "(Figura X)" do texto sai (ver
_sem_mencao_ao_mapa). No modo congelado a primeira página de estado e de área também vem
de um texto estático (primeira_pagina_da_unidade). A área tem o seu Doc desde 23/11/2026
(services/primeira_pagina_area.py), convertido para o formato deste módulo.
"""

import html
import logging
import re

from fastapi import HTTPException

from config import CARACTERISTICAS_ESTADO_DOCS_URL
from services import relatorio_congelado
from services.primeira_pagina_area import primeira_pagina_da_area
from utils.cover import montar_indicadores_do_doc
from utils.external.docs import (
    CardDoPanorama,
    carregar_texto_do_docs,
    extrair_panorama_indicadores,
    extrair_relatorio_geral,
    extrair_resumo_cidade,
)
from utils.queries.estado import buscar_caracteristicas_estado
from utils.render.placeholders import (
    isolar_paragrafo_de_cada_condicao,
    substituir_placeholders,
)
from utils.render.renderer import (
    _legenda_mapa_localizacao_html,
    render_descricao_tema_html,
    resolver_referencia_figura_do_mapa,
)

logger = logging.getLogger(__name__)

NAMESPACE_PRIMEIRA_PAGINA = "geral"

# O ícone do card na capa (report/src/components/cover/MetricIcon.jsx) pelo campo do
# Doc: os mesmos dois do municipal (utils/cover.py, `metricas`).
# Na área (services/primeira_pagina_area.py) os campos têm o prefixo `area_`.
_ICONE_DA_METRICA = {
    "area": "area",
    "pop_total_2022": "populacao",
    "area_territorial_km2": "area",
    "area_pop_total_2022": "populacao",
}
# O texto estático traz o valor fixo, sem `$campo`: o ícone sai pelo rótulo.
_ICONE_DO_ROTULO = {"Área territorial": "area", "População residente": "populacao"}
_CAMPO_DO_CARD = re.compile(r"\$(\w+)")
# "56.467,243 km²" → valor "56.467,243", sufixo "km²": a capa desenha a unidade menor.
_VALOR_COM_UNIDADE = re.compile(r"^(.*\d)\s+(\D+)$")
# WARNING: sem mapa, a menção ao mapa ("Alagoas (Figura X) possui…") cairia no contador
# de figuras e roubaria o número do primeiro gráfico do relatório. Quando o mapa do
# estado existir, trocar por resolver_referencia_figura_do_mapa (utils/render/renderer.py),
# como no municipal.
_MENCAO_AO_MAPA = re.compile(r"\s*\(Figura\s+X\)")
# "Figura X – Localização da Paraíba (PB)." depois do bloco resumo_cidade.
_LEGENDA_DO_MAPA = re.compile(r"(?im)^[ \t]*Figura\s+\S+\s*[–-]\s*Localiza[cç][aã]o\b.*$")


async def primeira_pagina_do_estado(estado: str, safe_report: str) -> dict[str, object]:
    """As chaves da capa que o Doc da primeira página preenche, ou {} quando a
    variável não está configurada ou o estado não está em est_caract_mun.

    Ex.: (await primeira_pagina_do_estado("Paraíba", "relatorio_demografia__para_ba"))["metricas"][0]["rotulo"]
         == "Área territorial"
    """
    if not CARACTERISTICAS_ESTADO_DOCS_URL:
        return {}
    # Modo congelado (beta): a linha vem da pasta congelada, sem banco.
    if relatorio_congelado.ativo():
        linha = relatorio_congelado.caracteristicas_do_estado(estado)
    else:
        linha = buscar_caracteristicas_estado(estado)
    if linha is None:
        logger.warning("Relatório de %s: sem linha em est_caract_mun. Capa sem primeira página.", estado)
        return {}
    try:
        texto_do_doc = await carregar_texto_do_docs(CARACTERISTICAS_ESTADO_DOCS_URL)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    return montar_primeira_pagina(texto_do_doc, linha, safe_report)


async def primeira_pagina_da_unidade(
    unidade: str, nome: str, safe_report: str, mapa: str | None = None
) -> dict[str, object]:
    """As chaves da capa da primeira página de um estado ou área. No modo congelado vem do
    texto estático da unidade, com o mapa (`mapa`, PNG já em output); sem texto estático,
    o estado cai no Doc (primeira_pagina_do_estado) e a área fica sem primeira página.

    Ex.: (await primeira_pagina_da_unidade("area", "Caatinga", "r", "mapa_area_caatinga.png"))["mapa_principal"]
    """
    if relatorio_congelado.ativo():
        texto = relatorio_congelado.primeira_pagina(unidade, nome)
        if texto is not None:
            return montar_primeira_pagina(texto, {}, safe_report, mapa=mapa, nome=nome)
    capa = await _primeira_pagina_do_doc(unidade, nome, safe_report)
    if mapa:
        # Sem texto estático, o mapa ainda é a Figura 1 (o contador já contou com ele).
        capa["mapa_principal"] = figura_do_mapa(mapa, None, nome)
    return capa


async def _primeira_pagina_do_doc(unidade: str, nome: str, safe_report: str) -> dict[str, object]:
    """O Doc de primeira página da unidade: estado e área têm o seu; município não passa aqui."""
    if unidade == "estado":
        return await primeira_pagina_do_estado(nome, safe_report)
    if unidade == "area":
        return await primeira_pagina_da_area(nome, safe_report)
    return {}


def figura_do_mapa(mapa: str, legenda: str | None, nome: str) -> str:
    """O mapa de localização como Figura 1, no mesmo HTML do mapa municipal
    (render_mapa_marker), com o PNG em /output/.

    Ex.: "Figura 1 – Localização da Caatinga." in figura_do_mapa("m.png", "Figura X – Localização da Caatinga.", "Caatinga")
    """
    legenda_html = _legenda_mapa_localizacao_html(legenda or f"Figura 1 – Localização: {nome}.")
    return (
        '<figure class="map-block map-block--region">'
        f'<img class="region-map-image" src="/output/{html.escape(mapa)}" '
        f'alt="Mapa de localização: {html.escape(nome)}">'
        f"<figcaption>{legenda_html}</figcaption>"
        "</figure>"
    )


def montar_primeira_pagina(
    texto_do_doc: str,
    contexto: dict,
    safe_report: str,
    mapa: str | None = None,
    nome: str = "",
    isolar_condicoes: bool = True,
) -> dict[str, object]:
    """Fatia o Doc e resolve cada parte contra a linha do estado. Bloco ausente no Doc
    não vira chave, e a capa mantém o que tinha.

    Ex.: montar_primeira_pagina("apresentacao = “Panorama geral.$uf_de.” @@",
                                {"uf_de": "da Paraíba"}, "r")["relatorio_geral"]
         == "Panorama da Paraíba."
    """
    # No Doc estadual cada "Para quando … então:" vale só para a linha seguinte, como nos
    # Docs de tema (services/relatorio_estado.py, tema_da_unidade).
    # O Doc de área desliga (isolar_condicoes=False): lá a condição vale até a linha em branco.
    texto = isolar_paragrafo_de_cada_condicao(texto_do_doc) if isolar_condicoes else texto_do_doc
    cards, texto = extrair_panorama_indicadores(texto)
    apresentacao, texto = extrair_relatorio_geral(texto)
    resumo, resto = extrair_resumo_cidade(texto)
    capa: dict[str, object] = {}
    metricas = metricas_da_primeira_pagina(cards, contexto)
    if metricas:
        capa["metricas"] = metricas
    if mapa:
        legenda = _LEGENDA_DO_MAPA.search(resto)
        capa["mapa_principal"] = figura_do_mapa(mapa, legenda.group(0).strip() if legenda else None, nome)
        resumo = resolver_referencia_figura_do_mapa(resumo) if resumo else resumo
    else:
        resumo = _sem_mencao_ao_mapa(resumo)
    blocos = (("relatorio_geral", apresentacao), ("resumo_cidade", resumo))
    for chave, bloco in blocos:
        if bloco:
            capa.update(_bloco_da_capa(chave, bloco, contexto, safe_report))
    return capa


def metricas_da_primeira_pagina(cards: list[CardDoPanorama], contexto: dict) -> list[dict[str, str]]:
    """Os cards do Doc no formato de `cover.metricas` (rotulo, valor, sufixo, fonte,
    caption, icone). Card sem valor some, como em montar_indicadores_do_doc.

    Ex.: metricas_da_primeira_pagina([CardDoPanorama("Área territorial", "geral.$area:3 km²")],
                                     {"area": 56467.243})[0]["sufixo"] == "km²"
    """
    indicadores = montar_indicadores_do_doc(cards, contexto, NAMESPACE_PRIMEIRA_PAGINA)
    return [_metrica(card, indicador) for card, indicador in _pares_card_indicador(cards, indicadores)]


def _pares_card_indicador(
    cards: list[CardDoPanorama], indicadores: list[dict[str, str]]
) -> list[tuple[CardDoPanorama, dict[str, str]]]:
    """montar_indicadores_do_doc omite card sem valor; casa de volta pelo rótulo."""
    por_rotulo = {card.rotulo: card for card in cards}
    return [(por_rotulo[indicador["nome"]], indicador) for indicador in indicadores]


def _metrica(card: CardDoPanorama, indicador: dict[str, str]) -> dict[str, str]:
    valor, sufixo = indicador["valor"], ""
    com_unidade = _VALOR_COM_UNIDADE.match(valor)
    if com_unidade:
        valor, sufixo = com_unidade.group(1), com_unidade.group(2).strip()
    campo = _CAMPO_DO_CARD.search(card.valor)
    return {
        "rotulo": indicador["nome"],
        "valor": valor,
        "sufixo": sufixo,
        "fonte": indicador["fonte"],
        "caption": indicador["rodape"],
        "icone": _ICONE_DA_METRICA.get(campo.group(1), "") if campo else _ICONE_DO_ROTULO.get(indicador["nome"], ""),
    }


def _sem_mencao_ao_mapa(texto: str | None) -> str | None:
    return _MENCAO_AO_MAPA.sub("", texto) if texto else texto


def _bloco_da_capa(chave: str, bloco: str, contexto: dict, safe_report: str) -> dict[str, object]:
    return {
        chave: substituir_placeholders(bloco, contexto, NAMESPACE_PRIMEIRA_PAGINA),
        f"{chave}_html": render_descricao_tema_html(
            bloco, contexto, namespace=NAMESPACE_PRIMEIRA_PAGINA, safe_report=safe_report
        ),
    }
