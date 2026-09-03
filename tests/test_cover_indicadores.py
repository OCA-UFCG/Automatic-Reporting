from utils.cover import montar_indicadores_macrotema, montar_score_macrotema


def test_indicadores_diferem_entre_macrotemas():
    indicadores_saude = montar_indicadores_macrotema("Saúde")
    indicadores_educacao = montar_indicadores_macrotema("Educação")

    nomes_saude = {item["nome"] for item in indicadores_saude}
    nomes_educacao = {item["nome"] for item in indicadores_educacao}

    assert nomes_saude
    assert nomes_educacao
    assert nomes_saude.isdisjoint(nomes_educacao)


def test_indicadores_de_tema_sem_lista_especifica_usam_icone_do_tema():
    indicadores = montar_indicadores_macrotema("Instrumentos Sudene", macrotema_icone="chart")

    assert indicadores
    assert all(item["icone"] == "chart" for item in indicadores)


def test_score_usa_a_linha_do_tema_correspondente():
    score_demografia = montar_score_macrotema({"score_geral": "4,20"})
    score_saude = montar_score_macrotema({"score_geral": "1,80"})

    assert score_demografia["valor"] == "4,20"
    assert score_saude["valor"] == "1,80"


def test_score_usa_fallback_quando_coluna_ausente():
    score = montar_score_macrotema({})

    assert score["valor"] == "3,66"
    assert score["maximo"] == "5"
