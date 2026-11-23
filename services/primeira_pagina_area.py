"""Primeira página do relatório por área de interesse (23/11/2026): Apresentação, os
cards de área e população e Características Gerais, lidos de um Doc próprio
(CARACTERISTICAS_AREA_DOCS_URL) contra a linha da área.

É o equivalente de área de services/primeira_pagina_estado.py e reaproveita o mesmo
montador (montar_primeira_pagina). A diferença é o formato do Doc: a equipe escreveu o
Doc de área com os títulos "Apresentação" e "Características Gerais", sem os marcadores
`apresentacao = “…” @@` e `resumo_cidade = “…” @@` nem o título "Panorama de
indicadores". marcar_blocos_da_primeira_pagina converte esse formato no do estado; um
Doc que já traga os marcadores passa intacto.

Sem a variável configurada ou sem a linha da área, a capa fica como antes (só os blocos
de capa do Doc do primeiro tema, que nos Docs de área não existem).
"""

import logging
import re

from fastapi import HTTPException

from config import CARACTERISTICAS_AREA_DOCS_URL

# Módulo, não a função: primeira_pagina_estado importa este módulo (import circular).
from services import primeira_pagina_estado
from utils.external.docs import carregar_texto_do_docs, e_valor_de_card
from utils.queries.area import buscar_caracteristicas_area

logger = logging.getLogger(__name__)

# O export do Google começa com BOM (\ufeff), colado no título da primeira linha.
_TITULO_APRESENTACAO = re.compile(r"(?im)^[\ufeff \t]*Apresenta[cç][aã]o[ \t]*$")
_TITULO_CARACTERISTICAS = re.compile(r"(?im)^[ \t]*Caracter[ií]sticas\s+Gerais[ \t]*$")
_MARCADOR_DE_BLOCO = re.compile(r"(?im)^\s*(?:apresentacao|resumo_cidade)\s*=")
# "*Inserir figura": lembrete da equipe no Doc, não é marcador do relatório.
_LEMBRETE_DE_FIGURA = re.compile(r"(?im)^[ \t]*\*\s*inserir\s+figura\b.*$")
# "Figura 1 – Localização do Nordeste.": a legenda do mapa sai do texto e volta depois
# do bloco, onde montar_primeira_pagina a procura.
_LEGENDA_DO_MAPA = re.compile(r"(?im)^[ \t]*Figura\s+\S+\s*[–-]\s*Localiza[cç][aã]o\b.*$")
# WARNING: o Doc de área escreve "(Figura 1)", mas o 1 é do mapa. Sem mapa (gamma), só
# "(Figura X)" é apagado (primeira_pagina_estado._MENCAO_AO_MAPA); um "(Figura 1)" fixo
# apontaria para o primeiro gráfico do relatório. Na primeira página a única figura é o
# mapa, então trocar o número por X é seguro.
_FIGURA_UM = re.compile(r"\bFigura\s+1\b")


async def primeira_pagina_da_area(area: str, safe_report: str) -> dict[str, object]:
    """As chaves da capa que o Doc da primeira página de área preenche, ou {} quando a
    variável não está configurada ou a área não está no banco.

    Ex.: (await primeira_pagina_da_area("Caatinga", "relatorio_demografia__caatinga"))["metricas"][0]["rotulo"]
         == "Área territorial"
    """
    if not CARACTERISTICAS_AREA_DOCS_URL:
        return {}
    linha = buscar_caracteristicas_area(area)
    if linha is None:
        logger.warning("Relatório de %s: sem linha da área no banco. Capa sem primeira página.", area)
        return {}
    try:
        texto_do_doc = await carregar_texto_do_docs(CARACTERISTICAS_AREA_DOCS_URL)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    # INTENTIONAL: sem isolar as condições. No Doc de área cada "Para quando" vale até a
    # linha em branco, e o Nordeste tem dois parágrafos seguidos; isolando, o segundo
    # sairia nas quatro áreas.
    return primeira_pagina_estado.montar_primeira_pagina(
        marcar_blocos_da_primeira_pagina(texto_do_doc), linha, safe_report, isolar_condicoes=False
    )


def marcar_blocos_da_primeira_pagina(texto: str) -> str:
    """O Doc com títulos "Apresentação" / "Características Gerais" reescrito no formato
    marcado do Doc estadual. Doc já marcado, ou sem os dois títulos, volta intacto.

    Ex.: marcar_blocos_da_primeira_pagina("Apresentação\\nTexto.\\nÁrea\\ngeral.$a\\n"
                                          "Características Gerais\\nResumo.")
         == "Panorama de indicadores\\nÁrea\\ngeral.$a\\n\\napresentacao = “Texto.” @@\\n\\n"
            "resumo_cidade = “\\nResumo.\\n” @@"
    """
    if _MARCADOR_DE_BLOCO.search(texto):
        return texto
    apresentacao = _TITULO_APRESENTACAO.search(texto)
    caracteristicas = _TITULO_CARACTERISTICAS.search(texto)
    if apresentacao is None or caracteristicas is None or caracteristicas.start() < apresentacao.end():
        return texto
    paragrafos, cards = _separar_cards(texto[apresentacao.end():caracteristicas.start()])
    resumo, legenda = _resumo_e_legenda(texto[caracteristicas.end():])
    partes = [
        f"Panorama de indicadores\n{cards}" if cards else "",
        f"apresentacao = “{paragrafos}” @@" if paragrafos else "",
        f"resumo_cidade = “\n{resumo}\n” @@" if resumo else "",
        legenda,
    ]
    return "\n\n".join(parte for parte in partes if parte)


def _separar_cards(trecho: str) -> tuple[str, str]:
    """O texto da Apresentação e as linhas dos cards: os cards começam no primeiro
    rótulo cuja próxima linha não vazia é um valor (`$campo` ou número fixo)."""
    linhas = [linha.strip() for linha in trecho.split("\n") if linha.strip()]
    for indice in range(len(linhas) - 1):
        if "$" not in linhas[indice] and e_valor_de_card(linhas[indice + 1]):
            return "\n".join(linhas[:indice]), "\n".join(linhas[indice:])
    return "\n".join(linhas), ""


def _resumo_e_legenda(trecho: str) -> tuple[str, str]:
    """Características Gerais sem o lembrete de figura e sem a legenda do mapa, e a
    legenda à parte. As linhas em branco ficam: elas encerram cada condição."""
    legenda = _LEGENDA_DO_MAPA.search(trecho)
    sem_legenda = _LEGENDA_DO_MAPA.sub("", trecho) if legenda else trecho
    resumo = _FIGURA_UM.sub("Figura X", _LEMBRETE_DE_FIGURA.sub("", sem_legenda)).strip()
    return resumo, _FIGURA_UM.sub("Figura X", legenda.group(0).strip()) if legenda else ""
