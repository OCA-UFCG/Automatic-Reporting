from utils.cover import montar_indicadores_macrotema


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
