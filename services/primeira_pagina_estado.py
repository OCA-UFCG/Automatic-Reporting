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

Fica para depois: o mapa de localização do estado. Enquanto ele não existe, a menção
"(Figura X)" do texto sai (ver _sem_mencao_ao_mapa).
"""

import logging
import re

from fastapi import HTTPException

from config import CARACTERISTICAS_ESTADO_DOCS_URL
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
from utils.render.renderer import render_descricao_tema_html

logger = logging.getLogger(__name__)

NAMESPACE_PRIMEIRA_PAGINA = "geral"

# O ícone do card na capa (report/src/components/cover/MetricIcon.jsx) pelo campo do
# Doc: os mesmos dois do municipal (utils/cover.py, `metricas`).
_ICONE_DA_METRICA = {"area": "area", "pop_total_2022": "populacao"}
_CAMPO_DO_CARD = re.compile(r"\$(\w+)")
# "56.467,243 km²" → valor "56.467,243", sufixo "km²": a capa desenha a unidade menor.
_VALOR_COM_UNIDADE = re.compile(r"^(.*\d)\s+(\D+)$")
# WARNING: sem mapa, a menção ao mapa ("Alagoas (Figura X) possui…") cairia no contador
# de figuras e roubaria o número do primeiro gráfico do relatório. Quando o mapa do
# estado existir, trocar por resolver_referencia_figura_do_mapa (utils/render/renderer.py),
# como no municipal.
_MENCAO_AO_MAPA = re.compile(r"\s*\(Figura\s+X\)")


async def primeira_pagina_do_estado(estado: str, safe_report: str) -> dict[str, object]:
    """As chaves da capa que o Doc da primeira página preenche, ou {} quando a
    variável não está configurada ou o estado não está em est_caract_mun.

    Ex.: (await primeira_pagina_do_estado("Paraíba", "relatorio_demografia__para_ba"))["metricas"][0]["rotulo"]
         == "Área territorial"
    """
    if not CARACTERISTICAS_ESTADO_DOCS_URL:
        return {}
    linha = buscar_caracteristicas_estado(estado)
    if linha is None:
        logger.warning("Relatório de %s: sem linha em est_caract_mun. Capa sem primeira página.", estado)
        return {}
    try:
        texto_do_doc = await carregar_texto_do_docs(CARACTERISTICAS_ESTADO_DOCS_URL)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    return montar_primeira_pagina(texto_do_doc, linha, safe_report)


def montar_primeira_pagina(texto_do_doc: str, contexto: dict, safe_report: str) -> dict[str, object]:
    """Fatia o Doc e resolve cada parte contra a linha do estado. Bloco ausente no Doc
    não vira chave, e a capa mantém o que tinha.

    Ex.: montar_primeira_pagina("apresentacao = “Panorama geral.$uf_de.” @@",
                                {"uf_de": "da Paraíba"}, "r")["relatorio_geral"]
         == "Panorama da Paraíba."
    """
    # No Doc estadual cada "Para quando … então:" vale só para a linha seguinte, como nos
    # Docs de tema (services/relatorio_estado.py, tema_da_unidade).
    texto = isolar_paragrafo_de_cada_condicao(texto_do_doc)
    cards, texto = extrair_panorama_indicadores(texto)
    apresentacao, texto = extrair_relatorio_geral(texto)
    resumo, _ = extrair_resumo_cidade(texto)
    capa: dict[str, object] = {}
    metricas = metricas_da_primeira_pagina(cards, contexto)
    if metricas:
        capa["metricas"] = metricas
    blocos = (("relatorio_geral", apresentacao), ("resumo_cidade", _sem_mencao_ao_mapa(resumo)))
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
        "icone": _ICONE_DA_METRICA.get(campo.group(1) if campo else "", ""),
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
