from utils.queries import hidraulica


def test_buscar_tecnologias_acesso_agua_calcula_indicadores_historicos(monkeypatch):
    linhas = [
        (2010, 439, 439, 0),
        (2020, 1841, 1500, 341),
        (2025, 2038, 1600, 438),
    ]

    monkeypatch.setattr(
        hidraulica, "executar_query", lambda *args, **kwargs: linhas
    )
    resultado = hidraulica.buscar_tecnologias_acesso_agua("Cidade X", "PB")

    assert resultado is not None
    assert resultado["tecnologias_acesso_agua_serie"] == [
        {"ano": 2010, "total": 439},
        {"ano": 2020, "total": 1841},
        {"ano": 2025, "total": 2038},
    ]
    assert resultado["total_2010"] == 439
    assert resultado["total_2020"] == 1841
    assert resultado["total_2025"] == 2038
    assert resultado["acrescimo_qtd"] == 1599
    assert resultado["var_total_per"] == round(1599 / 439 * 100, 1)
    # Segunda década (2020-2025) cresceu menos que a primeira (2010-2020)
    assert resultado["dec_concentracao"] == "2010 a 2020"
    assert resultado["dec_concentracao_per"] == round(1402 / 1599 * 100, 1)

    # Finalidade calculada com base no último ano disponível (2025)
    assert resultado["primeira_agua_qtd"] == 1600
    assert resultado["primeira_agua_per"] == round(1600 / 2038 * 100, 1)
    assert resultado["segunda_agua_qtd"] == 438
    assert resultado["segunda_agua_per"] == round(438 / 2038 * 100, 1)
    assert resultado["sol_predom"] == "abastecimento humano (1ª água)"
    assert resultado["sol_predom_per"] == resultado["primeira_agua_per"]


def test_buscar_tecnologias_acesso_agua_predominio_de_segunda_agua(monkeypatch):
    linhas = [(2025, 1000, 200, 800)]

    monkeypatch.setattr(
        hidraulica, "executar_query", lambda *args, **kwargs: linhas
    )
    resultado = hidraulica.buscar_tecnologias_acesso_agua("Cidade X", "PB")

    assert resultado is not None
    assert resultado["sol_predom"] == "irrigação e dessedentação de animais (2ª água)"
    assert resultado["sol_predom_per"] == resultado["segunda_agua_per"] == 80.0


def test_buscar_tecnologias_acesso_agua_sem_ano_inicial_nao_calcula_variacao(monkeypatch):
    linhas = [(2020, 1841, 1500, 341), (2025, 2038, 1600, 438)]

    monkeypatch.setattr(
        hidraulica, "executar_query", lambda *args, **kwargs: linhas
    )
    resultado = hidraulica.buscar_tecnologias_acesso_agua("Cidade X", "PB")

    assert resultado is not None
    assert resultado["total_2020"] == 1841
    assert resultado["total_2025"] == 2038
    assert "total_2010" not in resultado
    assert "acrescimo_qtd" not in resultado
    assert "var_total_per" not in resultado


def test_buscar_tecnologias_acesso_agua_sem_dados_retorna_none(monkeypatch):
    monkeypatch.setattr(hidraulica, "executar_query", lambda *args, **kwargs: [])
    assert hidraulica.buscar_tecnologias_acesso_agua("Cidade X", "PB") is None
