"""Condições com "e" que juntam uma comparação entre campos e outra com número.

"$a for menor que $b e $a for maior que 0" chegava inteira ao avaliador
numérico, que só compara campo com campo quando a regra tem exatamente dois
campos: o "menor que $b" era descartado e a regra valia sempre que $a > 0.
No Doc de Meio Ambiente (revisão de 06/10/2026), os parágrafos de ASD em queda
e de ASD estável saíam juntos em 1.219 municípios.
"""

import pytest

from utils.render.placeholders import (
    conferir_condicoes,
    interpretar_blocos_condicionais,
)


def _vale(expressao: str, contexto: dict) -> bool:
    texto = f"Para quando {expressao}:\nTrecho.\n"
    return "Trecho." in interpretar_blocos_condicionais(texto, contexto)


@pytest.mark.parametrize(
    ("a", "b", "esperado"),
    [(50, 60, True), (60, 60, False), (70, 60, False), (0, 60, False)],
)
def test_menor_que_campo_e_maior_que_numero(a, b, esperado):
    assert _vale("$a for menor que $b e $a for maior que 0", {"a": a, "b": b}) is esperado


@pytest.mark.parametrize(
    ("a", "b", "esperado"),
    [(60, 60, True), (50, 60, False), (70, 60, False), (0, 0, False)],
)
def test_igual_a_campo_e_maior_que_numero(a, b, esperado):
    assert _vale("$a for igual a $b e $a for maior que 0", {"a": a, "b": b}) is esperado


@pytest.mark.parametrize(
    ("a", "b", "esperado"),
    [(50, 60, True), (60, 60, False), (0, 60, False)],
)
def test_ordem_invertida(a, b, esperado):
    assert _vale("$a for maior que 0 e $a for menor que $b", {"a": a, "b": b}) is esperado


@pytest.mark.parametrize(
    ("a", "b", "c", "esperado"),
    [(3, 2, 1, True), (3, 2, 2, False), (2, 2, 1, False)],
)
def test_duas_comparacoes_entre_campos(a, b, c, esperado):
    assert _vale("$a for maior que $b e $b for maior que $c", {"a": a, "b": b, "c": c}) is esperado


def test_regra_do_doc_com_prefixo_e_entao():
    regra = (
        "ambiente.$asd_per_2021 for menor que ambiente.$asd_per_1991 e "
        "ambiente.$asd_per_2021 for maior que 0, então"
    )
    queda = {"asd_per_2021": 95.22, "asd_per_1991": 99.71}
    estavel = {"asd_per_2021": 97.48, "asd_per_1991": 97.48}
    assert _vale(regra, {"ambiente": queda, **queda}) is True
    assert _vale(regra, {"ambiente": estavel, **estavel}) is False


def test_operador_compartilhado_continua_pelo_caminho_antigo():
    # "$a e $b for maior que 0": um operador para os dois campos.
    assert _vale("$a e $b for maior que 0", {"a": 1, "b": 2}) is True
    assert _vale("$a e $b for maior que 0", {"a": 1, "b": 0}) is False


def test_campo_sem_dado_derruba_a_comparacao_entre_campos():
    assert _vale("$a for igual a $b e $a for maior que 0", {"a": 60, "b": None}) is False


def test_conferir_condicoes_entende_a_forma_mista():
    texto = "Para quando $a for menor que $b e $a for maior que 0, então:\nTrecho.\n"
    assert conferir_condicoes(texto) == []
