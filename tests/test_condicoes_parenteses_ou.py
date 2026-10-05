"""Condições "Para quando ...:" com "ou" (disjunção) e parênteses (precedência).

"e" liga mais forte que "ou"; parênteses mudam a ordem e podem se aninhar.
"maior ou igual a" / "menor ou igual a" / "maior ou menor que" não são "ou".
"""

import pytest

from utils.render.placeholders import (
    conferir_condicoes,
    interpretar_blocos_condicionais,
)

_UM = "for igual a 1"


def _vale(expressao: str, contexto: dict) -> bool:
    texto = f"Para quando {expressao}:\nTrecho.\n"
    return "Trecho." in interpretar_blocos_condicionais(texto, contexto)


def _ctx(a: int = 0, b: int = 0, c: int = 0, **extra) -> dict:
    return {"a": a, "b": b, "c": c, **extra}


@pytest.mark.parametrize(
    ("a", "b", "esperado"),
    [(1, 0, True), (0, 1, True), (1, 1, True), (0, 0, False)],
)
def test_ou_basta_uma_das_comparacoes(a, b, esperado):
    assert _vale(f"$a {_UM} ou $b {_UM}", _ctx(a=a, b=b)) is esperado


def test_ou_aceita_mais_de_duas_alternativas():
    expressao = f"$a {_UM} ou $b {_UM} ou $c {_UM}"
    assert _vale(expressao, _ctx(c=1)) is True
    assert _vale(expressao, _ctx()) is False


@pytest.mark.parametrize(
    ("a", "b", "c", "esperado"),
    [
        (1, 0, 0, True),  # a sozinho basta: "e" liga mais forte, mas só entre b e c
        (0, 1, 1, True),
        (0, 1, 0, False),
        (0, 0, 1, False),
    ],
)
def test_e_tem_precedencia_sobre_ou(a, b, c, esperado):
    assert _vale(f"$a {_UM} ou $b {_UM} e $c {_UM}", _ctx(a=a, b=b, c=c)) is esperado


@pytest.mark.parametrize(
    ("a", "b", "c", "esperado"),
    [
        (1, 0, 0, False),  # os parênteses forçam o "e" com c
        (1, 0, 1, True),
        (0, 1, 1, True),
        (0, 0, 1, False),
    ],
)
def test_parenteses_mudam_a_precedencia(a, b, c, esperado):
    assert _vale(f"($a {_UM} ou $b {_UM}) e $c {_UM}", _ctx(a=a, b=b, c=c)) is esperado


@pytest.mark.parametrize(
    ("a", "b", "c", "esperado"),
    [(0, 1, 0, False), (0, 1, 1, True), (1, 0, 1, True), (1, 1, 0, False)],
)
def test_grupo_entre_parenteses_pode_ficar_a_direita(a, b, c, esperado):
    assert _vale(f"$c {_UM} e ($a {_UM} ou $b {_UM})", _ctx(a=a, b=b, c=c)) is esperado


def test_parenteses_aninhados():
    expressao = f"$a {_UM} ou (($b {_UM} ou $c {_UM}) e $d {_UM})"
    assert _vale(expressao, _ctx(c=1, d=1)) is True
    assert _vale(expressao, _ctx(c=1, d=0)) is False
    assert _vale(expressao, _ctx(a=1)) is True


def test_parenteses_em_volta_da_condicao_inteira():
    assert _vale(f"($a {_UM} ou $b {_UM})", _ctx(b=1)) is True
    assert _vale(f"(($a {_UM}))", _ctx()) is False


def test_dois_grupos_ligados_por_e():
    expressao = f"($a {_UM} ou $b {_UM}) e ($c {_UM} ou $d {_UM})"
    assert _vale(expressao, _ctx(a=1, d=1)) is True
    assert _vale(expressao, _ctx(a=1)) is False


def test_e_composto_sem_parenteses_continua_valendo_dentro_do_grupo():
    # "$a e $b for ..." (operador compartilhado) segue pelo caminho antigo.
    assert _vale(f"($a e $b for maior que 0) ou $c {_UM}", _ctx(a=1, b=2)) is True
    assert _vale(f"($a e $b for maior que 0) ou $c {_UM}", _ctx(a=1, b=0)) is False


def test_maior_ou_igual_nao_e_disjuncao():
    expressao = "$a for maior ou igual a 5 e $b for menor ou igual a 2"
    assert _vale(expressao, _ctx(a=5, b=2)) is True
    assert _vale(expressao, _ctx(a=4, b=2)) is False


def test_maior_ou_igual_convive_com_ou():
    expressao = "$a for maior ou igual a 5 ou $b for menor ou igual a 2"
    assert _vale(expressao, _ctx(a=9, b=9)) is True
    assert _vale(expressao, _ctx(a=0, b=1)) is True
    assert _vale(expressao, _ctx(a=0, b=9)) is False


def test_campo_sem_dado_so_derruba_a_alternativa_dele():
    # centro_pop é null-sensível: sem dado, a comparação sobre ele não vale,
    # mas a outra alternativa do "ou" ainda pode valer.
    contexto = _ctx(a=1, centro_pop=None)
    assert _vale(f"$centro_pop for igual a 0 ou $a {_UM}", contexto) is True
    assert _vale(f"$centro_pop for igual a 0 e $a {_UM}", contexto) is False
    assert _vale(f"$centro_pop for igual a 0 ou $b {_UM}", contexto) is False


def test_ou_com_condicao_de_vacina():
    contexto = _ctx(a=1, vacina_meta="algumas")
    assert _vale(f"$vacina_meta for todas ou $a {_UM}", contexto) is True
    assert _vale(f"$vacina_meta for todas ou $b {_UM}", contexto) is False


def test_ou_com_condicao_sem_dados():
    contexto = _ctx(a=0, esgoto_rede_2000="sem dados")
    assert _vale(f"$esgoto_rede_2000 for sem dados ou $a {_UM}", contexto) is True
    assert _vale(f"$esgoto_rede_2000 for sem dados e $a {_UM}", contexto) is False


def test_versoes_alternativas_do_paragrafo_com_ou_nao_vazam_juntas():
    texto = (
        f"Para quando $a {_UM} ou $b {_UM}:\nVersão A.\n\n"
        f"Para quando $a for igual a 0 e $b for igual a 0:\nVersão B.\n"
    )
    resultado = interpretar_blocos_condicionais(texto, _ctx(b=1))
    assert "Versão A." in resultado
    assert "Versão B." not in resultado


def test_parenteses_desbalanceados_viram_aviso_e_a_regra_nao_vale():
    expressao = f"($a {_UM} ou $b {_UM}"
    assert _vale(expressao, _ctx(a=1)) is False
    avisos = conferir_condicoes(f"Para quando {expressao}:\nTrecho.\n")
    assert len(avisos) == 1
    assert "parênteses" in avisos[0]


def test_parenteses_fechando_sem_abrir_viram_aviso():
    avisos = conferir_condicoes(f"Para quando $a {_UM}) ou $b {_UM}:\nTrecho.\n")
    assert len(avisos) == 1
    assert "parênteses" in avisos[0]


def test_alternativa_vazia_vira_aviso():
    avisos = conferir_condicoes(f"Para quando $a {_UM} ou :\nTrecho.\n")
    assert len(avisos) == 1
    assert "ou" in avisos[0]


def test_conferir_condicoes_aceita_ou_e_parenteses_bem_formados():
    doc = f"Para quando ($a {_UM} ou $b {_UM}) e $c {_UM}:\nTrecho.\n"
    assert conferir_condicoes(doc) == []


def test_conferir_condicoes_avisa_da_alternativa_nao_entendida():
    avisos = conferir_condicoes("Para quando $a for igual a 1 ou $b for bonito:\nTrecho.\n")
    assert len(avisos) == 1
    assert "$b" in avisos[0]
