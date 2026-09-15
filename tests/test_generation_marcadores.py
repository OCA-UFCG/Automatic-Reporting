import re

from services.generation import GRAFICOS_AUTO_MARCADOR


def test_legenda_visao_historica_aceita_a_redacao_atual_do_doc():
    # O Doc de demografia usa "Dinâmica populacional" (não mais "Visão
    # histórica da população"); sem o regex atualizado junto, o gráfico é
    # gerado mas nunca entra no relatório ("no caption in the Doc → no
    # chart", CLAUDE.md).
    _, padrao = next(
        item
        for item in GRAFICOS_AUTO_MARCADOR["demografia"]
        if item[0] == "grafico_visao_historica"
    )

    assert re.match(padrao, "Figura Z – Dinâmica populacional de X (UF)")
