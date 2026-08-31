from utils.queries import economia_renda


def test_buscar_indicadores_economia_calcula_variacao_e_setor_maior(monkeypatch):
    linha_banco = (
        1_000_000_000.0,  # pib_2010
        12_945_093_200.0,  # pib_2023
        25_000.0,  # pibcapita_2023
        1_000_000.0,  # vab_agropecuaria
        3_000_000.0,  # vab_industria
        9_500_000.0,  # vab_servicos (maior)
        2_000_000.0,  # vab_adm_publica
        850_000_000.0,  # imposto
    )
    monkeypatch.setattr(
        economia_renda, "executar_query", lambda *args, **kwargs: linha_banco
    )

    dados = economia_renda.buscar_indicadores_economia("Campina Grande", "PB")

    assert dados["pib_2010"] == 1_000_000_000.0
    assert dados["pib_unid_2023"] == "bilhões"
    assert round(dados["pib_2023"], 2) == round(12_945_093_200.0 / 1e9, 2)
    assert dados["pibcapita_unid_2023"] == "mil"
    assert round(dados["pibcapita_2023"], 2) == round(25_000.0 / 1e3, 2)

    variacao_nominal_esperada = 12_945_093_200.0 - 1_000_000_000.0
    variacao_percentual_esperada = variacao_nominal_esperada / 1_000_000_000.0 * 100
    assert dados["analise1_pib"] == variacao_nominal_esperada
    assert round(dados["analise1_pib_per"], 2) == round(variacao_percentual_esperada, 2)

    assert dados["setor2021_maior"] == "Serviços"
    assert dados["setor2021_maior_unid"] == "milhões"
    assert round(dados["setor2021"], 2) == round(9_500_000.0 / 1e6, 2)

    assert dados["imposto_unid"] == "milhões"
    assert round(dados["imposto"], 2) == round(850_000_000.0 / 1e6, 2)


def test_buscar_indicadores_economia_retorna_none_sem_dados(monkeypatch):
    monkeypatch.setattr(economia_renda, "executar_query", lambda *args, **kwargs: None)

    dados = economia_renda.buscar_indicadores_economia("Cidade Sem Dados", "PB")

    assert dados is None


def test_buscar_indicadores_economia_retorna_none_quando_agregacao_so_traz_nulos(monkeypatch):
    linha_banco_sem_correspondencia = (None, None, None, None, None, None, None, None)
    monkeypatch.setattr(
        economia_renda,
        "executar_query",
        lambda *args, **kwargs: linha_banco_sem_correspondencia,
    )

    dados = economia_renda.buscar_indicadores_economia("Cidade Fora Do Eco Pib", "PB")

    assert dados is None
