"""Condições que comparam rótulos de texto, não números.

O Doc de Instrumentos da Sudene escreve "$analise1_qtdcontrato_2024_2025 for
diferente de manutenção" e "$qtdprograma1 for igual a $valor_programa1", com
valores como "crescimento" e "FNE PNMPO". O avaliador só entendia número: sem
número dos dois lados, as duas alternativas do parágrafo davam falso e sumiam
juntas (Recife (PE), 28/10/2026).
"""

import pytest

from utils.render.placeholders import (
    conferir_condicoes,
    interpretar_blocos_condicionais,
)


def _vale(expressao: str, contexto: dict) -> bool:
    texto = f"Para quando {expressao}, então:\nTrecho.\n"
    return "Trecho." in interpretar_blocos_condicionais(texto, contexto)


@pytest.mark.parametrize(
    ("valor", "igual", "diferente"),
    [
        ("manutenção", True, False),
        ("crescimento", False, True),
        ("diminuição", False, True),
        # Caixa e espaço sobrando não mudam o rótulo.
        ("  Manutenção ", True, False),
    ],
)
def test_campo_contra_texto(valor, igual, diferente):
    contexto = {"analise1": valor}
    assert _vale("instrsudene.$analise1 for igual a manutenção", contexto) is igual
    assert _vale("instrsudene.$analise1 for diferente de manutenção", contexto) is diferente


def test_texto_com_artigo_e_literal():
    # analise3 vem com artigo da view ("uma manutenção"); o Doc escreve igual.
    contexto = {"analise3": "uma manutenção"}
    assert _vale("$analise3 for igual a uma manutenção", contexto)
    assert not _vale("$analise3 for diferente de uma manutenção", contexto)
    assert not _vale("$analise3 for igual a manutenção", contexto)


@pytest.mark.parametrize("valor", [None, "", "sem dados", float("nan")])
def test_campo_sem_dado_nao_vale_nem_igual_nem_diferente(valor):
    # Sem contratações nos dois anos, a view devolve NULL: nenhuma das duas
    # versões do parágrafo pode afirmar "manutenção" ou "variação".
    contexto = {"analise1": valor}
    assert not _vale("$analise1 for igual a manutenção", contexto)
    assert not _vale("$analise1 for diferente de manutenção", contexto)


@pytest.mark.parametrize(
    ("programa_qtd", "programa_valor", "igual"),
    [
        ("FNE PNMPO", "FNE-SERVICOS", False),
        # A view devolve qtdprograma1 com espaços à direita.
        ("FNE PNMPO      ", "FNE PNMPO", True),
        ("fne pnmpo", "FNE PNMPO", True),
    ],
)
def test_campo_contra_campo_de_texto(programa_qtd, programa_valor, igual):
    contexto = {"qtdprograma1": programa_qtd, "valor_programa1": programa_valor}
    assert _vale("$qtdprograma1 for igual a $valor_programa1", contexto) is igual
    assert _vale("$qtdprograma1 for diferente de $valor_programa1", contexto) is not igual


def test_campo_contra_campo_de_texto_sem_dado_nao_vale():
    contexto = {"qtdprograma1": "FNE PNMPO", "valor_programa1": None}
    assert not _vale("$qtdprograma1 for igual a $valor_programa1", contexto)
    assert not _vale("$qtdprograma1 for diferente de $valor_programa1", contexto)


def test_maior_que_entre_textos_nao_compara_ordem_alfabetica():
    contexto = {"a": "crescimento", "b": "diminuição"}
    assert not _vale("$a for maior que $b", contexto)
    assert not _vale("$a for menor que $b", contexto)


def test_campo_numerico_contra_texto_nao_vale():
    assert not _vale("$contrato2025 for igual a manutenção", {"contrato2025": 3})


def test_comparacao_numerica_continua_igual():
    assert _vale("$contrato2025 for maior que 1", {"contrato2025": 4341})
    assert _vale("$contrato2025 for igual a 1", {"contrato2025": 1})
    assert _vale("$a for igual a $b", {"a": 2, "b": 2.0})


def test_conferir_condicoes_entende_comparacao_com_texto():
    texto = (
        "Para quando instrsudene.$analise1 for diferente de manutenção, então:\n"
        "Trecho.\n"
        "Para quando instrsudene.$qtdprograma1 for igual a instrsudene.$valor_programa1, então:\n"
        "Trecho.\n"
    )
    assert conferir_condicoes(texto) == []


@pytest.mark.parametrize(
    ("qtd", "empate", "igual", "diferente"),
    [
        (3149, "empate", True, False),
        (3149, "não", False, True),
        # O fator numérico continua valendo: com uma empresa só, nenhuma versão.
        (1, "empate", False, False),
    ],
)
def test_e_com_fator_numerico_e_fator_de_texto(qtd, empate, igual, diferente):
    # Doc de Instrumentos da Sudene: o "e" só separava fatores quando algum
    # comparava dois campos, então essa regra ia inteira para o avaliador
    # numérico e nunca valia (conferência de 05/11/2026).
    contexto = {"qtd_empresa1": qtd, "empresa_empate": empate}
    regra = "instrsudene.$qtd_empresa1 for maior que 1 e instrsudene.$empresa_empate for {} empate"
    assert _vale(regra.format("igual a"), contexto) is igual
    assert _vale(regra.format("diferente de"), contexto) is diferente


def test_e_com_fator_de_texto_sem_dado_nao_vale():
    contexto = {"qtd_empresa1": 3149, "empresa_empate": None}
    assert not _vale("$qtd_empresa1 for maior que 1 e $empresa_empate for igual a empate", contexto)
    assert not _vale("$qtd_empresa1 for maior que 1 e $empresa_empate for diferente de empate", contexto)


def test_conferir_condicoes_aceita_e_com_texto_e_aponta_operador_errado():
    certo = "Para quando $qtd_empresa1 for maior que 1 e $empresa_empate for igual a empate, então:\nTrecho.\n"
    assert conferir_condicoes(certo) == []
    # "diferenre" (erro de digitação no Doc) não é operador: a conferência
    # precisa continuar apontando, em vez de a regra sumir calada.
    errado = certo.replace("igual a", "diferenre de")
    assert conferir_condicoes(errado) != []
