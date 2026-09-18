"""As views de perfil e de indicadores escrevem strings-sentinela em vez de
NULL quando não têm o dado. A normalização vive na fronteira
(`utils/queries/base.executar_query_dict`), para que nenhum consumidor —
capa, prosa ou gráfico — precise conhecer essas strings. Nenhum teste aqui
toca o banco.
"""

import pytest

from utils.cover import montar_indicadores_macrotema
from utils.formatting import limpar_sentinelas, valor_sem_sentinela
from utils.render.placeholders import substituir_placeholders

SENTINELAS = [
    "Não há dados",
    "Não há dados.",
    "não há dados",
    "nao ha dados",
    "Sem dados",
    "Sem informação",
    "Não informado",
    "N/D",
    "-",
    "--",
    "  Não há dados  ",
]


@pytest.mark.parametrize("sentinela", SENTINELAS)
def test_sentinela_da_view_vira_none(sentinela):
    assert valor_sem_sentinela(sentinela) is None


@pytest.mark.parametrize(
    "valor",
    [
        "3",
        "0",
        "590.55",
        0,
        3,
        # Contraexemplo: a comparação é por igualdade, não por substring. Um
        # texto editorial que *menciona* a ausência de dados é conteúdo, não
        # sentinela, e não pode ser apagado.
        "Não há dados suficientes para o município",
        "Sem dados de 2010, apenas de 2022",
    ],
)
def test_valor_legitimo_atravessa_intacto(valor):
    assert valor_sem_sentinela(valor) == valor


def test_limpar_sentinelas_normaliza_a_linha_inteira():
    linha = {
        "valor_uc": "Não há dados",
        "n_uc": "Não há dados",
        "valor_asd": "590.55",
        "nm_uc": "Unidades de conservação",
    }

    assert limpar_sentinelas(linha) == {
        "valor_uc": None,
        "n_uc": None,
        "valor_asd": "590.55",
        "nm_uc": "Unidades de conservação",
    }


@pytest.mark.parametrize("sentinela", SENTINELAS)
def test_sentinela_nao_vira_card_com_unidade_colada(sentinela):
    """Antes, o card saía como "Não há dados. ha": só a string exata era
    filtrada, e qualquer variante vazava com a unidade grudada."""
    contexto = {
        "nm_uc_area": "Área em unidades de conservação",
        "valor_uc_area": sentinela,
        "fonte_uc_area": "CNUC (2025)",
        "unid_uc_area": "Área protegida no município (ha)",
    }

    nomes = {card["nome"] for card in montar_indicadores_macrotema("meio-ambiente", contexto)}

    assert "Área em unidades de conservação" not in nomes


def test_sentinela_nao_vaza_para_a_prosa():
    """O filtro antigo existia só na capa: o card sumia, mas o texto seguia
    afirmando "o município tem Não há dados unidades". Agora o $placeholder
    fica literal — bug visível, não frase falsa."""
    contexto = limpar_sentinelas({"n_uc": "Não há dados"})

    resultado = substituir_placeholders(
        "O município tem ambiente.$n_uc unidades.", contexto, "meio-ambiente"
    )

    assert "Não há dados" not in resultado
    assert "$n_uc" in resultado


def test_executar_query_dict_normaliza_a_linha_na_fronteira():
    """Antes do cache: senão o sentinela ficaria congelado por todo o TTL."""
    from unittest.mock import MagicMock, patch

    from utils.queries import base

    base.limpar_cache_queries()

    cursor = MagicMock()
    cursor.fetchone.return_value = ("Não há dados", "590.55")
    cursor.description = [("valor_uc",), ("valor_asd",)]
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False
    conn = MagicMock()
    conn.cursor.return_value = cursor

    try:
        with patch.object(base, "get_connection", return_value=conn):
            linha = base.executar_query_dict("SELECT 1", ("x",), "teste")
    finally:
        base.limpar_cache_queries()

    assert linha == {"valor_uc": None, "valor_asd": "590.55"}
