import re

from services.generation import GRAFICOS_AUTO_MARCADOR


def test_legenda_visao_historica_aceita_redacao_antiga_e_a_nova():
    # O título do card virou "Dinâmica Populacional" (plotting/demografia.py),
    # mas a legenda do Doc de produção ainda usa a redação antiga ("Visão
    # histórica da população..."). O regex precisa casar as duas: se um editor
    # atualizar a legenda pra combinar com o título novo sem coordenar com o
    # código, o gráfico não pode sumir do relatório sem erro nenhum.
    _, padrao = next(
        item
        for item in GRAFICOS_AUTO_MARCADOR["demografia"]
        if item[0] == "grafico_visao_historica"
    )

    assert re.match(
        padrao, "Figura Z – Visão histórica da população do município de X (UF)"
    )
    assert re.match(padrao, "Figura 3 – Dinâmica Populacional de X (UF)")
