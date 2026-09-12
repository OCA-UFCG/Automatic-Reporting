"""Adaptador: de onde vem a prosa editorial de um macrotema.

Este módulo é o *seam* do docs/PLANO-PAINEL-EDITORIAL.md. Tudo a jusante —
services/generation.py, utils/render/renderer.py, o SSR e o WeasyPrint —
continua recebendo exatamente o mesmo texto marcado de sempre; o que muda é
quem o produz:

- ``FONTE_EDITORIAL=docs`` (padrão): delega para
  ``utils.external.docs.carregar_texto_do_docs``. Caminho de produção, intacto.
- ``FONTE_EDITORIAL=painel``: lê o contrato publicado, avalia as regras contra o
  contexto do município e serializa de volta para o mesmo formato.

A escolha é por macrotema, via ``FONTE_EDITORIAL_<SLUG>``, para que a migração
aconteça um tema por vez enquanto o resto do time segue trabalhando nos Docs.
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from config import CONTRATOS_DIR, FONTE_EDITORIAL, require_config_value
from utils.editorial.contrato import exigir_contrato_valido
from utils.editorial.fontes import escolha_do_painel
from utils.editorial.render import (
    CHAVE_FONTE_PAINEL,
    FONTE_PAINEL,
    renderizar_contrato,
)
from utils.external.docs import carregar_texto_do_docs

logger = logging.getLogger(__name__)

FONTE_DOCS = "docs"
FONTES_VALIDAS = (FONTE_DOCS, FONTE_PAINEL)

# Contrato já validado, indexado por (slug, mtime): o artefato publicado muda
# raramente e revalidar a árvore inteira a cada município seria desperdício.
_cache_contratos: dict[tuple[str, float], dict[str, Any]] = {}

# Contrato ainda não publicado, válido só durante uma requisição de prévia.
# É um ContextVar e não uma global porque o processo atende várias requisições
# ao mesmo tempo: a prévia de um editor não pode vazar para o relatório que
# outra pessoa está gerando no mesmo instante.
_contrato_em_edicao: ContextVar[tuple[str, dict[str, Any]] | None] = ContextVar(
    "contrato_em_edicao", default=None
)


@contextmanager
def contrato_em_edicao(macrotema_slug: str, contrato: dict[str, Any]):
    """Faz o pipeline usar este contrato em vez do publicado, só aqui dentro.

    É o que permite a prévia do painel ser o relatório de verdade — mesma
    montagem de contexto, mesmos gráficos, mesmo SSR — com a prosa que o editor
    ainda está escrevendo. Fora deste bloco nada muda: o relatório de produção
    continua lendo o contrato publicado (ou o Google Doc).
    """
    token = _contrato_em_edicao.set((macrotema_slug, contrato))
    try:
        yield
    finally:
        _contrato_em_edicao.reset(token)


class ContratoIndisponivel(RuntimeError):
    """O macrotema está marcado como 'painel' mas não há contrato publicado."""


def variavel_de_ambiente(macrotema_slug: str) -> str:
    """Nome da variável de ambiente que governa este macrotema."""
    return f"FONTE_EDITORIAL_{macrotema_slug.upper().replace('-', '_')}"


def fonte_do_ambiente(macrotema_slug: str) -> str:
    """``docs`` ou ``painel`` segundo a variável de ambiente — a chave-mestra.

    Lida com ``os.environ`` a cada chamada, e não uma vez na importação, para
    que dar ``FONTE_EDITORIAL_EDUCACAO=painel`` na linha de comando de um teste
    ou de um script surta efeito sem reiniciar o processo.
    """
    especifica = os.getenv(variavel_de_ambiente(macrotema_slug))
    escolhida = (especifica or FONTE_EDITORIAL or FONTE_DOCS).strip().casefold()
    if escolhida not in FONTES_VALIDAS:
        logger.warning(
            "FONTE_EDITORIAL inválida para '%s': %r. Usando '%s'.",
            macrotema_slug,
            escolhida,
            FONTE_DOCS,
        )
        return FONTE_DOCS
    return escolhida


def fonte_editorial(macrotema_slug: str) -> str:
    """A fonte que vale para este macrotema agora.

    A variável de ambiente manda: enquanto ela estiver em ``docs``, é ``docs``,
    e o botão do painel não muda nada — trocar a origem da prosa de um relatório
    público é decisão de operação, não de um clique na tela. Com ela em
    ``painel``, a escolha registrada pelo painel decide tema a tema, e o padrão
    de quem nunca alternou continua sendo ``painel``, como era antes do botão.
    """
    do_ambiente = fonte_do_ambiente(macrotema_slug)
    if do_ambiente != FONTE_PAINEL:
        return do_ambiente

    escolhida = escolha_do_painel(macrotema_slug)
    if escolhida in FONTES_VALIDAS:
        return escolhida
    if escolhida:
        logger.warning(
            "Escolha de fonte inválida para '%s' em _fontes.json: %r. Usando '%s'.",
            macrotema_slug,
            escolhida,
            FONTE_PAINEL,
        )
    return FONTE_PAINEL


def alternavel_no_painel(macrotema_slug: str) -> bool:
    """O botão do painel tem efeito neste tema? Só com a chave-mestra ligada."""
    return fonte_do_ambiente(macrotema_slug) == FONTE_PAINEL


def caminho_do_contrato(macrotema_slug: str):
    return CONTRATOS_DIR / f"{macrotema_slug}.json"


def carregar_contrato_publicado(macrotema_slug: str) -> dict[str, Any]:
    """Artefato publicado do macrotema, validado.

    Hoje o artefato é um arquivo em ``output/contratos/``, escrito pelo
    importador. Quando o painel entrar (Fase 2), a publicação passa a vir da
    tabela em schema próprio no Postgres e só esta função muda — o resto do
    adaptador não sabe de onde o contrato veio.
    """
    caminho = caminho_do_contrato(macrotema_slug)
    if not caminho.exists():
        raise ContratoIndisponivel(
            f"'{macrotema_slug}' está com FONTE_EDITORIAL=painel, mas não há "
            f"contrato publicado em {caminho}. Gere um com: "
            f"python scripts/importar_doc.py --macrotema {macrotema_slug} --do-cache"
        )

    chave = (macrotema_slug, caminho.stat().st_mtime)
    if chave in _cache_contratos:
        return _cache_contratos[chave]

    contrato = exigir_contrato_valido(
        json.loads(caminho.read_text(encoding="utf-8"))
    )
    _cache_contratos.clear()
    _cache_contratos[chave] = contrato
    return contrato


async def carregar_texto_editorial(
    macrotema_slug: str, macrotema_dados: dict, contexto: dict
) -> str:
    """Texto marcado do macrotema, venha ele do Google Doc ou do painel.

    ``contexto`` é a linha de dados já resolvida do município. No caminho
    ``painel`` ela é necessária para avaliar as regras — e recebe a marca
    ``_fonte_editorial``, que impede ``interpretar_blocos_condicionais`` de
    reinterpretar um texto cujas condicionais já foram resolvidas aqui.
    """
    # A prévia vem antes de tudo: o editor precisa ver o efeito da alteração
    # mesmo quando o macrotema ainda é servido pelo Google Doc em produção.
    em_edicao = _contrato_em_edicao.get()
    if em_edicao is not None and em_edicao[0] == macrotema_slug:
        contexto[CHAVE_FONTE_PAINEL] = FONTE_PAINEL
        return renderizar_contrato(em_edicao[1], contexto)

    fonte = fonte_editorial(macrotema_slug)

    if fonte == FONTE_DOCS:
        docs_url = require_config_value(
            macrotema_dados["docs_url"], macrotema_dados["docs_env"]
        )
        return await carregar_texto_do_docs(docs_url)

    contrato = carregar_contrato_publicado(macrotema_slug)
    contexto[CHAVE_FONTE_PAINEL] = FONTE_PAINEL
    logger.info(
        "Macrotema '%s': prosa vinda do painel (contrato versão %s).",
        macrotema_slug,
        contrato.get("versao"),
    )
    return renderizar_contrato(contrato, contexto)
