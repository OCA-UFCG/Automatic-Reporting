import pytest

from utils.editorial.regras import (
    OPERADORES,
    ROTULOS_OPERADORES,
    avaliar_regra,
    validar_regra,
)


def _regra(campo, op, valor=None, sem_dado=None):
    condicao = {"campo": campo, "op": op}
    if valor is not None:
        condicao["valor"] = valor
    regra = {"condicoes": [condicao]}
    if sem_dado:
        regra["sem_dado"] = sem_dado
    return regra


@pytest.mark.parametrize(
    ("op", "valor", "casos"),
    [
        ("maior", 0, {5: True, 0: False, -5: False}),
        ("menor", 0, {5: False, 0: False, -5: True}),
        ("maior_igual", 0.5, {0.5: True, 0.6: True, 0.4: False}),
        ("menor_igual", 0.5, {0.5: True, 0.4: True, 0.6: False}),
        ("igual", 0, {0: True, 1: False}),
        ("diferente", 0, {0: False, 1: True, -1: True}),
        ("entre", [1, 3], {1: True, 2: True, 3: True, 0: False, 4: False}),
    ],
)
def test_cada_operador_avalia_como_o_nome_diz(op, valor, casos):
    for entrada, esperado in casos.items():
        resultado = avaliar_regra(_regra("x", op, valor), {"x": entrada})
        assert resultado.inclui is esperado, f"{op} {valor} com x={entrada}"


def test_diferente_de_zero_cobre_valores_positivos():
    """O Doc escreve "maior ou menor que 0%" querendo "≠ 0"; o parser por regex
    casa "menor que 0" antes e esconde o bloco em municípios com crescimento
    positivo. O operador nomeado resolve os dois lados."""
    regra = _regra("cres_pop_analise", "diferente", 0)

    assert avaliar_regra(regra, {"cres_pop_analise": 5}).inclui is True
    assert avaliar_regra(regra, {"cres_pop_analise": -5}).inclui is True
    assert avaliar_regra(regra, {"cres_pop_analise": 0}).inclui is False


def test_existe_distingue_ausencia_de_zero():
    """`centro_pop` = 0 significa "não tem Centro POP"; ausente significa "não
    sabemos". Hoje a diferença é uma lista fixa de nomes dentro do Python."""
    assert avaliar_regra(_regra("centro_pop", "existe"), {"centro_pop": 0}).inclui is True
    assert avaliar_regra(_regra("centro_pop", "existe"), {}).inclui is False
    assert avaliar_regra(_regra("centro_pop", "nao_existe"), {}).inclui is True


def test_campo_ausente_esconde_o_bloco_por_padrao():
    assert avaliar_regra(_regra("x", "maior", 0), {}).inclui is False


def test_campo_ausente_pode_render_texto_alternativo():
    regra = _regra(
        "pop_rua_2022",
        "maior",
        0,
        sem_dado={"acao": "texto_alternativo", "texto": "Sem registros."},
    )
    resultado = avaliar_regra(regra, {})

    assert resultado.inclui is False
    assert resultado.texto_alternativo == "Sem registros."


def test_condicoes_sao_combinadas_com_e():
    regra = {
        "condicoes": [
            {"campo": "a", "op": "maior", "valor": 0},
            {"campo": "b", "op": "igual", "valor": 0},
        ]
    }
    assert avaliar_regra(regra, {"a": 1, "b": 0}).inclui is True
    assert avaliar_regra(regra, {"a": 1, "b": 1}).inclui is False


def test_regra_nula_sempre_inclui():
    assert avaliar_regra(None, {}).inclui is True


def test_valor_com_virgula_decimal_e_lido_como_numero():
    """O Gini vem dos Docs como "0,5"; a leitura tem de ser numérica."""
    assert avaliar_regra(_regra("gini", "maior_igual", 0.5), {"gini": "0,6"}).inclui is True


def test_validacao_recusa_operador_desconhecido_e_valor_faltando():
    assert validar_regra({"condicoes": [{"campo": "x", "op": "quase"}]})
    assert validar_regra({"condicoes": [{"campo": "x", "op": "maior"}]})
    assert validar_regra({"condicoes": []})
    assert validar_regra({"condicoes": [{"campo": "x", "op": "entre", "valor": [1]}]})


def test_validacao_aceita_regra_bem_formada():
    assert validar_regra(_regra("x", "entre", [1, 3])) == []
    assert validar_regra(_regra("x", "existe")) == []


def test_todo_operador_tem_rotulo_para_o_painel():
    assert set(OPERADORES) == set(ROTULOS_OPERADORES)


def test_condicao_pode_comparar_dois_campos():
    """O Doc de Educação pede "Para quando $sem_instr_2000 for igual a
    $sem_instr_2022:". O parser dos Docs não compara campo com campo, e o
    parágrafo some do relatório em todo município."""
    regra = {
        "condicoes": [
            {
                "campo": "sem_instr_2000",
                "op": "igual",
                "valor": {"campo": "educacao.sem_instr_2022"},
            }
        ]
    }

    assert avaliar_regra(regra, {"sem_instr_2000": 100, "sem_instr_2022": 100}).inclui
    assert not avaliar_regra(regra, {"sem_instr_2000": 100, "sem_instr_2022": 50}).inclui


def test_campo_de_comparacao_ausente_conta_como_sem_dado():
    regra = {
        "condicoes": [
            {"campo": "a", "op": "maior", "valor": {"campo": "b"}}
        ],
        "sem_dado": {"acao": "texto_alternativo", "texto": "Sem comparação."},
    }
    resultado = avaliar_regra(regra, {"a": 10})

    assert resultado.inclui is False
    assert resultado.texto_alternativo == "Sem comparação."


def test_validacao_recusa_referencia_a_campo_malformada():
    assert validar_regra(
        {"condicoes": [{"campo": "a", "op": "igual", "valor": {"coluna": "b"}}]}
    )
    assert (
        validar_regra(
            {"condicoes": [{"campo": "a", "op": "igual", "valor": {"campo": "b"}}]}
        )
        == []
    )
