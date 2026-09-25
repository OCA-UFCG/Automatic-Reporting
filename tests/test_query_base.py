import pytest

from utils.queries.base import (
    escalar_valor,
    escalar_valor_por_extenso,
    unidade_de_massa,
)


@pytest.mark.parametrize(
    ("valor", "unidade"),
    [
        (1_700_000, "milhão"),
        (1_000_000_000, "bilhão"),
        (2_000_000, "milhões"),
        # Exibido como "2,00".
        (1_999_000, "milhões"),
        (5_000, "mil"),
        (617, ""),
    ],
)
def test_escalar_valor_por_extenso_concorda_com_o_numero(valor, unidade):
    assert escalar_valor_por_extenso(valor)[1] == unidade


def test_escalar_valor_segue_no_plural_para_os_graficos():
    assert escalar_valor(1_700_000)[1] == "milhões"


def test_escalar_valor_por_extenso_sem_valor():
    assert escalar_valor_por_extenso(None) == (None, None)


@pytest.mark.parametrize(
    ("unidade", "esperado"),
    [("milhões", "milhões de"), ("bilhão", "bilhão de"), ("mil", "mil"), ("", "")],
)
def test_unidade_de_massa(unidade, esperado):
    assert unidade_de_massa(unidade) == esperado
