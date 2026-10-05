from utils.queries import economia_renda


def test_processar_indicadores_economia_calcula_variacao_e_setores_maiores(monkeypatch):
    # linha de 2021: vab_agropecuaria=1_000_000, vab_industria=3_000_000,
    # vab_servicos=9_500_000, vab_adm_publica=2_000_000 (já em reais, depois de
    # convertidos de milhares) -> ranking esperado: Serviços > Indústria >
    # Administração Pública > Agropecuária. vab_*/impostos_liquidos chegam do
    # banco em milhares de reais, por isso os valores brutos abaixo vêm /1000.
    linhas_banco = [
        (2010, 1_000_000_000.0, None, None, None, None, None, None),
        (2021, None, None, 1_000.0, 3_000.0, 9_500.0, 2_000.0, 850_000.0),
        (2023, 12_945_093_200.0, 25_000.0, None, None, None, None, None),
    ]
    monkeypatch.setattr(
        economia_renda, "executar_query", lambda *args, **kwargs: linhas_banco
    )

    linhas = economia_renda.buscar_linhas_pib_municipal("Campina Grande", "PB")
    dados = economia_renda.processar_indicadores_economia(linhas)

    assert dados["pib_unid_2010"] == "bilhão"
    assert round(dados["pib_2010"], 2) == round(1_000_000_000.0 / 1e9, 2)
    assert dados["pib_unid_2023"] == "bilhões"
    assert round(dados["pib_2023"], 2) == round(12_945_093_200.0 / 1e9, 2)
    assert dados["pibcapita_unid_2023"] == "mil"
    assert round(dados["pibcapita_2023"], 2) == round(25_000.0 / 1e3, 2)

    variacao_nominal_esperada = 12_945_093_200.0 - 1_000_000_000.0
    variacao_percentual_esperada = variacao_nominal_esperada / 1_000_000_000.0 * 100
    assert dados["analise1_pib"] == "aumento"
    assert dados["diferenca_pib_2010_2023unid"] == "bilhões"
    assert round(dados["diferenca_pib_2010_2023"], 2) == round(variacao_nominal_esperada / 1e9, 2)
    assert round(dados["pib_per_2010_2023"], 2) == round(variacao_percentual_esperada, 2)

    assert dados["setor2021_maior1"] == "Serviços"
    assert dados["setor2021_maior1unid"] == "milhões"
    assert round(dados["setor2021_maior1_vab"], 2) == round(9_500_000.0 / 1e6, 2)

    assert dados["setor2021_maior2"] == "Indústria"
    assert dados["setor2021_maior2unid"] == "milhões"
    assert round(dados["setor2021_maior2_vab"], 2) == round(3_000_000.0 / 1e6, 2)

    assert dados["setor2021_maior3"] == "Administração Pública"
    assert dados["setor2021_maior3unid"] == "milhões"
    assert round(dados["setor2021_maior3_vab"], 2) == round(2_000_000.0 / 1e6, 2)

    assert dados["imposto_unid"] == "milhões"
    assert round(dados["imposto"], 2) == round(850_000_000.0 / 1e6, 2)


def test_processar_indicadores_economia_usa_reducao_quando_pib_cai(monkeypatch):
    linhas_banco = [
        (2010, 2_000_000_000.0, None, None, None, None, None, None),
        (2023, 1_500_000_000.0, None, None, None, None, None, None),
    ]
    monkeypatch.setattr(
        economia_renda, "executar_query", lambda *args, **kwargs: linhas_banco
    )

    linhas = economia_renda.buscar_linhas_pib_municipal("Cidade em Queda", "PB")
    dados = economia_renda.processar_indicadores_economia(linhas)

    assert dados["analise1_pib"] == "redução"
    # escalar_valor só escala magnitudes positivas; negativo chega bruto (sem unidade)
    assert dados["diferenca_pib_2010_2023unid"] == ""
    assert round(dados["diferenca_pib_2010_2023"], 2) == -500_000_000.0
    assert round(dados["pib_per_2010_2023"], 2) == round(-500_000_000.0 / 2_000_000_000.0 * 100, 2)


def test_processar_indicadores_economia_calcula_atividade_maior_participacao(monkeypatch):
    # pib_total já em reais; vab_*/impostos_liquidos/vab_setor_maior em
    # milhares de reais, por isso vêm /1000 dos valores em reais esperados.
    linhas_banco = [
        (
            2021,
            260_030_930.0,
            None,
            1_000.0,
            3_000.0,
            9_500.0,
            2_000.0,
            850_000.0,
            "Administração, defesa, educação e saúde públicas e seguridade social",
            66.669,
        ),
    ]
    monkeypatch.setattr(
        economia_renda, "executar_query", lambda *args, **kwargs: linhas_banco
    )

    linhas = economia_renda.buscar_linhas_pib_municipal("Banabuiú", "CE")
    dados = economia_renda.processar_indicadores_economia(linhas)

    assert (
        dados["ativ_participacao_pib"]
        == "Administração, defesa, educação e saúde públicas e seguridade social"
    )
    assert round(dados["ativ_participacao_pibper"], 2) == round(
        66_669.0 / 260_030_930.0 * 100, 2
    )


def test_processar_indicadores_economia_expoe_vab_bruto_dos_4_setores_fixos(monkeypatch):
    # vab_* chegam do banco em milhares de reais; os valores brutos abaixo
    # (/1000 dos reais esperados) são convertidos para reais no processamento.
    linhas_banco = [
        (2021, 1_081_180_000.0, None, 101_700.0, 225_830.0, 493_420.0, 260_230.0, None, None, None),
    ]
    monkeypatch.setattr(
        economia_renda, "executar_query", lambda *args, **kwargs: linhas_banco
    )

    linhas = economia_renda.buscar_linhas_pib_municipal("Recife", "PE")
    dados = economia_renda.processar_indicadores_economia(linhas)

    assert dados["vab_setores_2021"] == {
        "agropecuaria": 101_700_000.0,
        "industria": 225_830_000.0,
        "servicos": 493_420_000.0,
        "adm_publica": 260_230_000.0,
    }


def test_processar_indicadores_economia_converte_vab_de_milhares_para_reais(monkeypatch):
    # Regressão: eco_pib.pib_municipal expõe vab_*/impostos_liquidos/vab_setor_maior
    # em milhares de reais. Dados reais de Carnaubais (RN), 2021: a soma dos 4
    # setores + impostos, em milhares, bate com pib_total (em reais) do mesmo
    # ano/município. Sem a conversão para reais, "R$ 74,99 milhões" de VAB da
    # Indústria aparecia como "R$ 74,99 mil" no texto e na Figura de VAB por setor.
    linhas_banco = [
        (
            2021,
            210_950_481.0,
            19_226.26,
            12_107.0,
            74_994.0,
            47_259.0,
            69_037.0,
            7_554.0,
            "Indústrias extrativas",
            74_994.0,
        ),
    ]
    monkeypatch.setattr(
        economia_renda, "executar_query", lambda *args, **kwargs: linhas_banco
    )

    linhas = economia_renda.buscar_linhas_pib_municipal("Carnaubais", "RN")
    dados = economia_renda.processar_indicadores_economia(linhas)

    assert dados["vab_setores_2021"] == {
        "agropecuaria": 12_107_000.0,
        "industria": 74_994_000.0,
        "servicos": 47_259_000.0,
        "adm_publica": 69_037_000.0,
    }
    assert dados["imposto_unid"] == "milhões"
    assert round(dados["imposto"], 2) == 7.55
    assert round(dados["ativ_participacao_pibper"], 2) == round(
        74_994_000.0 / 210_950_481.0 * 100, 2
    )


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


def test_nome_do_setor_vem_da_view_com_preposicao():
    # Regressão: o nome local ("Serviços") sobrescrevia o da view ("de Serviços")
    # e o Doc, que escreve "setor economia.$setor2021_maior1" sem o "de", saía
    # "setor Serviços" (revisão de Economia, Rosário do Catete, 05/10/2026).
    from services.generation import _economia_sem_sobrescrever_view

    local = {
        "setor2021_maior1": "Serviços",
        "setor2021_maior1_vab": 9.5,
        "setor2021_maior1unid": "milhões",
        "setor2021_maior2": "Administração Pública",
        "setor2021_maior3": "Indústria",
        "pib_2023": 12.3,
    }
    view = {
        "setor2021_maior1": "de Serviços",
        "setor2021_maior1unid": "milhões",
        "setor2021_maior2": "da Administração pública",
        "setor2021_maior3": "da Indústria",
    }

    linha = dict(view)
    linha.update(_economia_sem_sobrescrever_view(local, view))

    assert linha["setor2021_maior1"] == "de Serviços"
    assert linha["setor2021_maior2"] == "da Administração pública"
    assert linha["setor2021_maior3"] == "da Indústria"
    # valor e unidade continuam do cálculo local
    assert linha["setor2021_maior1_vab"] == 9.5
    assert linha["pib_2023"] == 12.3


def test_sem_view_nome_local_do_setor_vale():
    # Fallback CSV (PR #91): sem linha da view, o nome local continua saindo.
    from services.generation import _economia_sem_sobrescrever_view

    local = {"setor2021_maior1": "Serviços", "setor2021_maior1_vab": 9.5}
    assert _economia_sem_sobrescrever_view(local, None) == local


def test_variacao_do_pib_vem_da_view_sem_sinal():
    # Regressão: a variação local, com sinal, sobrescrevia a da view e o Doc saía
    # "houve redução nominal de R$ -224.929.200 … redução de -36,47%" (Rosário do
    # Catete, 05/10/2026). A view traz módulo + unidade e o sentido na palavra.
    from services.generation import _economia_sem_sobrescrever_view

    local = {
        "analise1_pib": "redução",
        "diferenca_pib_2010_2023": -224_929_200.0,
        "diferenca_pib_2010_2023unid": "",
        "pib_per_2010_2023": -36.47,
        "pib_2010": 616.81,
    }
    view = {
        "analise1_pib": "uma diminuição",
        "diferenca_pib_2010_2023": 224.93,
        "diferenca_pib_2010_2023unid": "milhões",
        "pib_per_2010_2023": 36.47,
    }

    linha = dict(view)
    linha.update(_economia_sem_sobrescrever_view(local, view))

    assert linha["analise1_pib"] == "uma diminuição"
    assert linha["diferenca_pib_2010_2023"] == 224.93
    assert linha["diferenca_pib_2010_2023unid"] == "milhões"
    assert linha["pib_per_2010_2023"] == 36.47
    assert linha["pib_2010"] == 616.81
