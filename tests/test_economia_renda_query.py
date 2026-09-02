from utils.queries import economia_renda


def test_processar_indicadores_economia_calcula_variacao_e_setores_maiores(monkeypatch):
    # linha de 2021: vab_agropecuaria=1_000_000, vab_industria=3_000_000,
    # vab_servicos=9_500_000, vab_adm_publica=2_000_000 -> ranking esperado:
    # Serviços > Indústria > Administração Pública > Agropecuária.
    linhas_banco = [
        (2010, 1_000_000_000.0, None, None, None, None, None, None),
        (2021, None, None, 1_000_000.0, 3_000_000.0, 9_500_000.0, 2_000_000.0, 850_000_000.0),
        (2023, 12_945_093_200.0, 25_000.0, None, None, None, None, None),
    ]
    monkeypatch.setattr(
        economia_renda, "executar_query", lambda *args, **kwargs: linhas_banco
    )

    linhas = economia_renda.buscar_linhas_pib_municipal("Campina Grande", "PB")
    dados = economia_renda.processar_indicadores_economia(linhas)

    assert dados["pib_unid_2010"] == "bilhões"
    assert round(dados["pib_2010"], 2) == round(1_000_000_000.0 / 1e9, 2)
    assert dados["pib_unid_2023"] == "bilhões"
    assert round(dados["pib_2023"], 2) == round(12_945_093_200.0 / 1e9, 2)
    assert dados["pibcapita_unid_2023"] == "mil"
    assert round(dados["pibcapita_2023"], 2) == round(25_000.0 / 1e3, 2)

    variacao_nominal_esperada = 12_945_093_200.0 - 1_000_000_000.0
    variacao_percentual_esperada = variacao_nominal_esperada / 1_000_000_000.0 * 100
    assert dados["analise1_pib_unid"] == "bilhões"
    assert round(dados["analise1_pib"], 2) == round(variacao_nominal_esperada / 1e9, 2)
    assert round(dados["analise1_pib_per"], 2) == round(variacao_percentual_esperada, 2)

    assert dados["setor2021_maior1"] == "Serviços"
    assert dados["setor2021_unid1"] == "milhões"
    assert round(dados["setor2021_valor1"], 2) == round(9_500_000.0 / 1e6, 2)

    assert dados["setor2021_maior2"] == "Indústria"
    assert dados["setor2021_unid2"] == "milhões"
    assert round(dados["setor2021_valor2"], 2) == round(3_000_000.0 / 1e6, 2)

    assert dados["setor2021_maior3"] == "Administração Pública"
    assert dados["setor2021_unid3"] == "milhões"
    assert round(dados["setor2021_valor3"], 2) == round(2_000_000.0 / 1e6, 2)

    assert dados["imposto_unid"] == "milhões"
    assert round(dados["imposto"], 2) == round(850_000_000.0 / 1e6, 2)


def test_processar_indicadores_economia_retorna_none_sem_dados(monkeypatch):
    monkeypatch.setattr(economia_renda, "executar_query", lambda *args, **kwargs: None)

    linhas = economia_renda.buscar_linhas_pib_municipal("Cidade Sem Dados", "PB")
    dados = economia_renda.processar_indicadores_economia(linhas)

    assert dados is None


def test_processar_indicadores_economia_retorna_none_quando_agregacao_so_traz_nulos(monkeypatch):
    linhas_banco_sem_correspondencia = [(2010, None, None, None, None, None, None, None)]
    monkeypatch.setattr(
        economia_renda,
        "executar_query",
        lambda *args, **kwargs: linhas_banco_sem_correspondencia,
    )

    linhas = economia_renda.buscar_linhas_pib_municipal("Cidade Fora Do Eco Pib", "PB")
    dados = economia_renda.processar_indicadores_economia(linhas)

    assert dados is None


def test_processar_pib_evolucao_e_indicadores_reaproveitam_a_mesma_consulta(monkeypatch):
    linhas_banco = [
        (2010, 166_512_845.0, None, None, None, None, None, None),
        (2021, None, None, 1_000_000.0, 3_000_000.0, 9_500_000.0, 2_000_000.0, 850_000_000.0),
        (2023, 12_945_093_200.0, 25_000.0, None, None, None, None, None),
    ]
    chamadas = []

    def executar_query_fake(*args, **kwargs):
        chamadas.append(args)
        return linhas_banco

    monkeypatch.setattr(economia_renda, "executar_query", executar_query_fake)

    linhas = economia_renda.buscar_linhas_pib_municipal("Campina Grande", "PB")
    dados_pib = economia_renda.processar_pib_evolucao(linhas)
    dados_indicadores = economia_renda.processar_indicadores_economia(linhas)

    assert len(chamadas) == 1
    assert dados_pib["pib_serie"] == [
        {"ano": 2010, "pib_total": 166_512_845.0},
        {"ano": 2023, "pib_total": 12_945_093_200.0},
    ]
    assert dados_indicadores["pib_unid_2010"] == "milhões"
