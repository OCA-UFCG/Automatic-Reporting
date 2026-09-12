"""Regras de exibição do painel editorial.

Substitui as frases livres ``Para quando ... :`` dos Google Docs por operadores
nomeados. A tabela abaixo deriva de ``_OPERADORES_EDITORIAIS``
(utils/render/placeholders.py), com duas correções que o parser por regex não
conseguia fazer:

- ``diferente`` existe de verdade. No Doc de demografia o editor escreveu
  "for maior ou menor que 0%" querendo dizer "≠ 0", e a regex de "menor que"
  casava antes, avaliando a condição como ``< 0`` — errado, em silêncio, para
  todo município com valor positivo.
- ``existe``/``nao_existe`` são explícitos. Hoje isso é uma lista fixa de nomes
  de coluna no Python (``_CAMPOS_NULL_SENSIVEIS = {"centro_pop", "n_uc"}``),
  onde ausência de dado não é o mesmo que zero.

O ``valor`` de uma condição pode ser um número, um texto ou **outro campo**,
na forma ``{"campo": "educacao.sem_instr_2022"}``. Comparar dois campos é
capacidade que o parser dos Docs não tem: escrever
``Para quando $sem_instr_2000 for igual a $sem_instr_2022:`` faz a condição
falhar e o parágrafo sumir do relatório em qualquer município — foi o que
aconteceu com o Doc de Educação.

A composição é sempre **E** entre as condições: sem OU e sem aninhamento, por
decisão de escopo (ver docs/PLANO-PAINEL-EDITORIAL.md §2).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from utils.formatting import coerce_para_float

# Importado do resolvedor do caminho Docs de propósito: a regra do painel
# precisa enxergar exatamente os mesmos campos que um $placeholder enxerga,
# incluindo aliases de namespace e percentuais derivados. Duplicar essa lógica
# aqui criaria divergência entre o que o operador testa e o que o texto mostra.
from utils.render.placeholders import _resolver_campo_com_alias

ACOES_SEM_DADO = ("esconder", "mostrar", "texto_alternativo")

# Operadores que não exigem valor porque testam a própria presença do dado.
OPERADORES_DE_PRESENCA = ("existe", "nao_existe")

OPERADORES_BINARIOS: dict[str, Callable[[float, float], bool]] = {
    "maior_igual": lambda v, n: v >= n,
    "menor_igual": lambda v, n: v <= n,
    "maior": lambda v, n: v > n,
    "menor": lambda v, n: v < n,
    "igual": lambda v, n: v == n,
    "diferente": lambda v, n: v != n,
}

OPERADORES = (*OPERADORES_BINARIOS, "entre", *OPERADORES_DE_PRESENCA)

# Rótulos em português para o painel montar o seletor sem hardcode no cliente;
# entram no /manifesto.
ROTULOS_OPERADORES = {
    "entre": "está entre",
    "maior_igual": "é maior ou igual a",
    "menor_igual": "é menor ou igual a",
    "maior": "é maior que",
    "menor": "é menor que",
    "igual": "é igual a",
    "diferente": "é diferente de",
    "existe": "tem valor",
    "nao_existe": "não tem valor",
}


@dataclass(frozen=True)
class ResultadoRegra:
    """O que o renderizador deve fazer com o bloco.

    ``inclui`` diz se o bloco entra. ``texto_alternativo`` só vem preenchido
    quando o dado faltou e o operador escolheu mostrar outra frase no lugar —
    é o que evita o placeholder cru vazando para o PDF.
    """

    inclui: bool
    texto_alternativo: str | None = None
    motivo: str = ""


INCLUI = ResultadoRegra(inclui=True)


def validar_regra(regra: Any) -> list[str]:
    """Erros de forma da regra; lista vazia significa válida."""
    erros: list[str] = []

    if not isinstance(regra, dict):
        return [f"regra deve ser objeto, veio {type(regra).__name__}"]

    condicoes = regra.get("condicoes")
    if not isinstance(condicoes, list) or not condicoes:
        erros.append("'condicoes' deve ser lista não vazia")
        condicoes = []

    for i, condicao in enumerate(condicoes):
        onde = f"condicoes[{i}]"
        if not isinstance(condicao, dict):
            erros.append(f"{onde}: deve ser objeto")
            continue

        if not isinstance(condicao.get("campo"), str) or not condicao.get("campo"):
            erros.append(f"{onde}: 'campo' obrigatório")

        op = condicao.get("op")
        if op not in OPERADORES:
            erros.append(f"{onde}: operador {op!r} desconhecido; use {list(OPERADORES)}")
            continue

        if op in OPERADORES_DE_PRESENCA:
            continue

        valor = condicao.get("valor")
        if op == "entre":
            if not isinstance(valor, (list, tuple)) or len(valor) != 2:
                erros.append(f"{onde}: 'entre' exige 'valor' com dois limites [a, b]")
            elif any(
                not _referencia_a_campo(v)
                and coerce_para_float(v, default=None) is None
                for v in valor
            ):
                erros.append(
                    f"{onde}: limites de 'entre' devem ser números ou "
                    "referências {'campo': ...}"
                )
        elif valor is None:
            erros.append(f"{onde}: operador {op!r} exige 'valor'")
        elif isinstance(valor, dict) and not _referencia_a_campo(valor):
            erros.append(
                f"{onde}: referência a campo deve ser {{'campo': 'nome'}}, veio {valor!r}"
            )

    sem_dado = regra.get("sem_dado")
    if sem_dado is not None:
        if not isinstance(sem_dado, dict):
            erros.append("'sem_dado' deve ser objeto")
        else:
            acao = sem_dado.get("acao")
            if acao not in ACOES_SEM_DADO:
                erros.append(
                    f"sem_dado.acao {acao!r} desconhecida; use {list(ACOES_SEM_DADO)}"
                )
            elif acao == "texto_alternativo" and not isinstance(
                sem_dado.get("texto"), str
            ):
                erros.append("sem_dado: ação 'texto_alternativo' exige 'texto'")

    return erros


def _referencia_a_campo(valor: Any) -> bool:
    return isinstance(valor, dict) and isinstance(valor.get("campo"), str)


def _resolver_alvo(valor: Any, contexto: dict) -> Any:
    """Resolve ``{"campo": "x"}`` contra o contexto; devolve literais como vieram."""
    if _referencia_a_campo(valor):
        return _resolver_campo_com_alias(contexto, valor["campo"].split(".")[-1])
    return valor


def _comparar(valor: Any, condicao: dict, contexto: dict) -> bool:
    op = condicao["op"]
    alvo = condicao.get("valor")

    if op == "entre":
        numero = coerce_para_float(valor, default=None)
        inicio = coerce_para_float(_resolver_alvo(alvo[0], contexto), default=None)
        fim = coerce_para_float(_resolver_alvo(alvo[1], contexto), default=None)
        if None in (numero, inicio, fim):
            return False
        return inicio <= numero <= fim

    alvo = _resolver_alvo(alvo, contexto)
    numero = coerce_para_float(valor, default=None)
    alvo_numero = coerce_para_float(alvo, default=None)

    # Comparação textual só faz sentido para igualdade; para os operadores de
    # ordem um valor não numérico é indecidível e a regra falha fechada.
    if numero is None or alvo_numero is None:
        if op == "igual":
            return str(valor).strip().casefold() == str(alvo).strip().casefold()
        if op == "diferente":
            return str(valor).strip().casefold() != str(alvo).strip().casefold()
        return False

    return OPERADORES_BINARIOS[op](numero, alvo_numero)


def avaliar_regra(regra: Any, contexto: dict) -> ResultadoRegra:
    """Decide se o bloco entra no relatório deste município.

    Um campo sem valor no ``contexto`` não é tratado como zero: cai na ação
    ``sem_dado`` da regra, que por padrão esconde o bloco. Esse é o
    comportamento que hoje só existe para os campos de
    ``_CAMPOS_NULL_SENSIVEIS`` e que o operador passa a controlar por bloco.
    """
    if regra is None:
        return INCLUI

    sem_dado = regra.get("sem_dado") or {"acao": "esconder"}

    for condicao in regra.get("condicoes", []):
        campo = condicao["campo"]
        # O campo pode vir qualificado ("educacao.matriculas"); o contexto é
        # plano, então o namespace é só rótulo de origem para o painel.
        campo_simples = campo.split(".")[-1]
        valor = _resolver_campo_com_alias(contexto, campo_simples)
        op = condicao["op"]

        if op == "existe":
            if valor is None:
                return ResultadoRegra(False, motivo=f"{campo} não tem valor")
            continue
        if op == "nao_existe":
            if valor is not None:
                return ResultadoRegra(False, motivo=f"{campo} tem valor")
            continue

        # Comparar com um campo que não existe neste município é tão "sem dado"
        # quanto faltar o campo da esquerda.
        referencia = condicao.get("valor")
        if (
            valor is not None
            and _referencia_a_campo(referencia)
            and _resolver_alvo(referencia, contexto) is None
        ):
            valor = None

        if valor is None:
            acao = sem_dado.get("acao", "esconder")
            if acao == "mostrar":
                continue
            if acao == "texto_alternativo":
                return ResultadoRegra(
                    False,
                    texto_alternativo=sem_dado.get("texto"),
                    motivo=f"{campo} sem dado",
                )
            return ResultadoRegra(False, motivo=f"{campo} sem dado")

        if not _comparar(valor, condicao, contexto):
            return ResultadoRegra(
                False, motivo=f"{campo} não atende {condicao['op']}"
            )

    return INCLUI
