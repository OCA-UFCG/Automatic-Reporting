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


# "não" nega o fator que vem logo depois e liga mais forte que "e" e "ou".


@pytest.mark.parametrize(("a", "esperado"), [(1, False), (0, True)])
def test_nao_nega_uma_comparacao(a, esperado):
    assert _vale(f"não $a {_UM}", _ctx(a=a)) is esperado


def test_nao_aceita_sem_til_e_em_maiuscula():
    assert _vale(f"NAO $a {_UM}", _ctx(a=0)) is True
    assert _vale(f"NÃO $a {_UM}", _ctx(a=1)) is False


@pytest.mark.parametrize(
    ("a", "b", "esperado"),
    [(0, 0, True), (1, 0, False), (0, 1, False), (1, 1, False)],
)
def test_nao_nega_o_grupo_entre_parenteses(a, b, esperado):
    assert _vale(f"não ($a {_UM} ou $b {_UM})", _ctx(a=a, b=b)) is esperado


@pytest.mark.parametrize(
    ("a", "b", "esperado"),
    [(1, 0, True), (1, 1, False), (0, 0, False), (0, 1, False)],
)
def test_e_nao(a, b, esperado):
    assert _vale(f"$a {_UM} e não $b {_UM}", _ctx(a=a, b=b)) is esperado


@pytest.mark.parametrize(
    ("a", "b", "esperado"),
    [(0, 0, True), (0, 1, False), (1, 1, True), (1, 0, True)],
)
def test_ou_nao(a, b, esperado):
    assert _vale(f"$a {_UM} ou não $b {_UM}", _ctx(a=a, b=b)) is esperado


def test_nao_liga_mais_forte_que_e():
    # (não a) e b, e não não (a e b)
    expressao = f"não $a {_UM} e $b {_UM}"
    assert _vale(expressao, _ctx(a=0, b=1)) is True
    assert _vale(expressao, _ctx(a=1, b=1)) is False
    assert _vale(expressao, _ctx(a=0, b=0)) is False


def test_nao_duplo_cancela():
    assert _vale(f"não não $a {_UM}", _ctx(a=1)) is True
    assert _vale(f"não (não $a {_UM})", _ctx(a=0)) is False


def test_nao_dentro_de_grupo_aninhado():
    expressao = f"($a {_UM} ou não $b {_UM}) e $c {_UM}"
    assert _vale(expressao, _ctx(a=0, b=0, c=1)) is True
    assert _vale(expressao, _ctx(a=0, b=1, c=1)) is False


def test_nao_com_maior_ou_igual():
    assert _vale("não $a for maior ou igual a 5", _ctx(a=4)) is True
    assert _vale("não $a for maior ou igual a 5", _ctx(a=5)) is False


def test_nao_sem_dado_nega_a_comparacao_que_nao_vale():
    # sem dado, "centro_pop igual a 0" não vale; logo "não" dela vale.
    assert _vale("não $centro_pop for igual a 0", _ctx(centro_pop=None)) is True


def test_nao_sem_operando_vira_aviso_e_a_regra_nao_vale():
    avisos = conferir_condicoes(f"Para quando $a {_UM} e não:\nTrecho.\n")
    assert len(avisos) == 1
    assert "não" in avisos[0]
    assert _vale(f"$a {_UM} e não", _ctx(a=1)) is False


def test_conferir_condicoes_aceita_nao_bem_formado():
    assert conferir_condicoes(f"Para quando $a {_UM} e não ($b {_UM} ou $c {_UM}):\nT.\n") == []


def test_conferir_condicoes_avisa_da_comparacao_nao_entendida_sob_nao():
    avisos = conferir_condicoes("Para quando não $a for bonito:\nTrecho.\n")
    assert len(avisos) == 1
    assert "$a" in avisos[0]


# O Doc fecha a regra com ", então" (ver docs/editorial); ele vem depois do ")".

_MORTALIDADE_ZERADA = (
    "saude.$mortalidade_2024 for igual a 0 e saude.$mortalidade_2025 for igual a 0 e "
    "(saude.$mortalidade_2010 for diferente de 0 ou saude.$mortalidade_2020 for diferente de  0 "
    "ou saude.$mortalidade_2021 for diferente de 0 ou saude.$mortalidade_2022 for diferente de  0 "
    "ou saude.$mortalidade_2023 for diferente de 0)"
)
_ANOS = (2010, 2020, 2021, 2022, 2023, 2024, 2025)


@pytest.mark.parametrize("fecho", ["", ", então", " então", ", ENTÃO"])
@pytest.mark.parametrize(
    ("diferentes_de_zero", "esperado"),
    [
        ({2022}, True),
        ({2010}, True),
        (set(), False),
        ({2022, 2024}, False),
        ({2025}, False),
    ],
)
def test_regra_de_mortalidade_com_grupo_de_ou_e_entao_no_fim(fecho, diferentes_de_zero, esperado):
    contexto = {f"mortalidade_{ano}": int(ano in diferentes_de_zero) for ano in _ANOS}
    assert _vale(_MORTALIDADE_ZERADA + fecho, contexto) is esperado


@pytest.mark.parametrize(
    "expressao",
    [
        f"$a {_UM} ou $b {_UM}, então",
        f"($a {_UM} ou $b {_UM}), então",
        f"não ($a {_UM} ou $b {_UM}), então",
    ],
)
def test_entao_no_fim_nao_atrapalha_ou_nem_parenteses(expressao):
    assert conferir_condicoes(f"Para quando {expressao}:\nTrecho.\n") == []
    assert _vale(expressao, _ctx(b=1)) is (not expressao.startswith("não"))
