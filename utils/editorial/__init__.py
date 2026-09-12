"""Painel editorial: contrato, regras e renderização.

Ver docs/PLANO-PAINEL-EDITORIAL.md. Nada aqui é usado pelo caminho Google Docs
— a escolha entre os dois é feita em utils/external/editorial.py pela flag
FONTE_EDITORIAL.
"""

from utils.editorial.contrato import (
    VERSAO_CONTRATO,
    ErroDeContrato,
    carregar_contrato,
    exigir_contrato_valido,
    novo_contrato,
    salvar_contrato,
    validar_contrato,
)
from utils.editorial.regras import (
    OPERADORES,
    ROTULOS_OPERADORES,
    ResultadoRegra,
    avaliar_regra,
    validar_regra,
)
from utils.editorial.render import (
    CHAVE_FONTE_PAINEL,
    FONTE_PAINEL,
    renderizar_contrato,
)

__all__ = [
    "CHAVE_FONTE_PAINEL",
    "FONTE_PAINEL",
    "OPERADORES",
    "ROTULOS_OPERADORES",
    "VERSAO_CONTRATO",
    "ErroDeContrato",
    "ResultadoRegra",
    "avaliar_regra",
    "carregar_contrato",
    "exigir_contrato_valido",
    "novo_contrato",
    "renderizar_contrato",
    "salvar_contrato",
    "validar_contrato",
    "validar_regra",
]
