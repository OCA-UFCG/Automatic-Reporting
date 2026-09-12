"""Escolha de fonte editorial feita **no painel**, macrotema a macrotema.

É a segunda camada da precedência; a primeira é a variável de ambiente, e ela
manda:

1. ``FONTE_EDITORIAL_<SLUG>`` (ou a global ``FONTE_EDITORIAL``) em ``painel``
   é a chave-mestra. Só com ela ligada a escolha registrada aqui vale.
2. Com a chave-mestra ligada, este arquivo decide tema a tema — é o botão do
   painel, que alterna um macrotema sem mexer no ambiente do servidor nem
   arrastar os outros sete junto.

Enquanto a variável de ambiente estiver em ``docs``, o que estiver gravado aqui
fica inerte: produção não muda de fonte por um clique na tela. Foi para isso que
a ordem é essa — trocar a origem da prosa de um relatório público é uma decisão
de operação, e o ambiente é onde ela é tomada.

O registro é um JSON ao lado dos contratos (``output/contratos/_fontes.json``).
O prefixo ``_`` evita colidir com ``<slug>.json``, que é o contrato publicado.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from config import CONTRATOS_DIR

logger = logging.getLogger(__name__)

NOME_DO_ARQUIVO = "_fontes.json"


def _caminho():
    return CONTRATOS_DIR / NOME_DO_ARQUIVO


def ler_escolhas() -> dict[str, Any]:
    """O registro inteiro, ``{slug: {"fonte", "em", "por"}}``.

    Arquivo ausente ou corrompido vira registro vazio: sem escolha registrada a
    fonte é a do ambiente, que é o comportamento de antes do painel.
    """
    caminho = _caminho()
    if not caminho.exists():
        return {}
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("Registro de fontes ilegível em %s; usando o ambiente.", caminho)
        return {}
    return dados if isinstance(dados, dict) else {}


def escolha_do_painel(macrotema_slug: str) -> str | None:
    """``docs``, ``painel`` ou ``None`` quando ninguém alternou este tema."""
    registro = ler_escolhas().get(macrotema_slug)
    if not isinstance(registro, dict):
        return None
    fonte = str(registro.get("fonte") or "").strip().casefold()
    return fonte or None


def registrar_escolha(macrotema_slug: str, fonte: str, editor: str) -> dict[str, Any]:
    """Grava a escolha e devolve o registro daquele tema.

    Guarda quem alternou e quando: a pergunta que aparece depois de um relatório
    sair diferente do esperado é "quem mudou isso?", e o arquivo é a única
    resposta que sobrevive a um restart.
    """
    escolhas = ler_escolhas()
    registro = {
        "fonte": fonte,
        "em": datetime.now().astimezone().isoformat(timespec="seconds"),
        "por": editor,
    }
    escolhas[macrotema_slug] = registro

    caminho = _caminho()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(escolhas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    logger.info("Fonte editorial de '%s' alternada para '%s' por %s", macrotema_slug, fonte, editor)
    return registro
