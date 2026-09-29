from utils.queries import demografia


def test_media_crescimento_mesmo_porte_nao_trunca_divisao_inteira():
    # Regressão: (pop_2022 - pop_2010) e pop_2010 são colunas inteiras; sem o
    # cast pra numeric, "/" era avaliado como divisão inteira ANTES do "* 100.0"
    # (mesma precedência, esquerda pra direita), truncando pra 0 qualquer
    # crescimento fracionário e zerando a média (bug real: PDF mostrou 0% onde
    # o banco tinha 11%).
    query = demografia.MEDIA_CRESCIMENTO_MESMO_PORTE
    divisao = query.split("AVG(", 1)[1].split(")\n", 1)[0]
    assert "::numeric" in divisao.split("/", 1)[0]


def test_buscar_demografia_sexo_faixa_etaria_usa_faixas_do_grafico(monkeypatch):
    # Regressão: cat_etaria_maior/menor citavam faixas de um agrupamento
    # diferente ("0 a 14", "30 a 59") que não existem na legenda do gráfico de
    # pirâmide etária (Figura 2), que usa décadas. Ambos devem vir da mesma
    # fonte de dados.
    linha_resumo = (
        1000,  # pop_total
        520,  # pop_mulher
        480,  # pop_homem
        100,  # pop_etaria_0_9
        150,  # pop_etaria_0_14
        200,  # pop_etaria_15_29
        400,  # pop_etaria_30_59
        250,  # pop_etaria_60_mais
        600,  # pop_branca
        200,  # pop_preta
        150,  # pop_parda
        30,  # pop_amarela
        20,  # pop_indigena
    )
    linhas_por_faixa = [
        ("0 a 9 anos", 40, 60, 1),
        ("10 a 19 anos", 45, 55, 2),
        ("20 a 29 anos", 90, 110, 3),
        ("30 a 39 anos", 150, 160, 4),  # maior faixa: 310
        ("40 a 49 anos", 60, 50, 5),
        ("50 a 59 anos", 40, 30, 6),
        ("60 a 69 anos", 30, 20, 7),
        ("70 a 79 anos", 15, 10, 8),
        ("80 anos ou mais", 5, 5, 9),  # menor faixa: 10
    ]

    respostas = iter([linha_resumo, linhas_por_faixa])
    monkeypatch.setattr(
        demografia,
        "executar_query",
        lambda *args, **kwargs: next(respostas),
    )

    resultado = demografia.buscar_demografia_sexo_faixa_etaria("Cidade X", "PB")

    assert resultado["cat_etaria_maior"] == "30 a 39 anos"
    assert resultado["etaria_maior"] == 310
    assert resultado["cat_etaria_menor"] == "80 anos ou mais"
    assert resultado["etaria_menor"] == 10


def test_faixas_etarias_empatadas_no_topo_viram_plural(monkeypatch):
    # Revisão da Etapa 2 (28/09/2026): o Doc escolhe "na faixa etária" x "nas
    # faixas etárias" por $qtd_faixas_etarias_maior. Com max() sozinho, um
    # empate citava só uma das faixas, escolhida pela ordem do dicionário.
    linha_resumo = (1000, 520, 480, 100, 150, 200, 400, 250, 600, 200, 150, 30, 20)
    linhas_por_faixa = [
        ("0 a 9 anos", 40, 60, 1),
        ("20 a 29 anos", 150, 160, 3),  # 310, empatada
        ("30 a 39 anos", 160, 150, 4),  # 310, empatada
        ("80 anos ou mais", 5, 5, 9),
    ]

    def buscar(linhas):
        respostas = iter([linha_resumo, linhas])
        monkeypatch.setattr(demografia, "executar_query", lambda *a, **k: next(respostas))
        return demografia.buscar_demografia_sexo_faixa_etaria("Cidade X", "PB")

    empate = buscar(linhas_por_faixa)
    assert empate["qtd_faixas_etarias_maior"] == 2
    assert empate["cat_etaria_maior"] == "20 a 29 anos e 30 a 39 anos"
    assert empate["etaria_maior"] == 310

    tres = buscar([*linhas_por_faixa, ("40 a 49 anos", 300, 10, 5)])
    assert tres["qtd_faixas_etarias_maior"] == 3
    assert tres["cat_etaria_maior"] == "20 a 29 anos, 30 a 39 anos e 40 a 49 anos"

    unica = buscar(linhas_por_faixa[:2])
    assert unica["qtd_faixas_etarias_maior"] == 1
    assert unica["cat_etaria_maior"] == "20 a 29 anos"


def test_cor_pri_class_concorda_no_plural_com_pessoas(monkeypatch):
    # Regressão: o Doc usa $cor_pri_class/$cor_raca_pri_class na frase
    # "predominância de pessoas autodeclaradas $cor_..." — "pessoas" no plural
    # exige "pardas", não "parda". O relatório de Recife (PE) saiu com
    # "pessoas autodeclaradas parda".
    linha_resumo = (
        1000, 520, 480, 100, 150, 200, 400, 250,
        200,  # pop_branca
        150,  # pop_preta
        600,  # pop_parda (maioria)
        30, 20,
    )
    respostas = iter([linha_resumo, []])
    monkeypatch.setattr(
        demografia,
        "executar_query",
        lambda *args, **kwargs: next(respostas),
    )

    resultado = demografia.buscar_demografia_sexo_faixa_etaria("Cidade X", "PB")

    assert resultado["cor_pri_class"] == "pardas"
    assert resultado["cor_raca_pri_class"] == "pardas"
    # $cor_seg_class etc. seguem no singular: aparecem em "a população $cor_seg_class".
    assert resultado["cor_seg_class"] == "branca"


def test_buscar_populacao_rua_distinguishes_confirmed_zero_from_no_data(monkeypatch):
    linha_zero = (2026, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    monkeypatch.setattr(
        demografia, "executar_query", lambda *args, **kwargs: [linha_zero]
    )
    resultado = demografia.buscar_populacao_rua("Cidade X", "PB")
    assert resultado is not None
    assert resultado["pop_rua_total"] == 0

    monkeypatch.setattr(demografia, "executar_query", lambda *args, **kwargs: [])
    assert demografia.buscar_populacao_rua("Cidade X", "PB") is None


def test_buscar_populacao_rua_zero_familias_total_nao_gera_zero_division(monkeypatch):
    # pop_rua_2022 presente, pop_rua_2026 ausente, familias_total == 0
    linha_2022 = (2022, 10, 1, 1, 1, 1, 0, 0, 5, 3, 2)

    monkeypatch.setattr(
        demografia, "executar_query", lambda *args, **kwargs: [linha_2022]
    )
    resultado = demografia.buscar_populacao_rua("Cidade X", "PB")

    assert resultado is not None
    assert "pop_rua_2026" not in resultado
    assert resultado["pop_rua_pobreza_per"] == 0.0
    assert resultado["pop_rua_br_per"] == 0.0
    assert resultado["pop_rua_acima_br_per"] == 0.0


def test_calculo_local_nao_sobrescreve_colunas_da_view():
    # Regressão: o relatório lia a vw_perfil_populacional_municipal e depois
    # sobrescrevia cres_pop/porte_mun/media_porte com o cálculo local, que tem
    # sinal e rótulos próprios — o Doc saía "apresentou uma redução de -5,3 %".
    from services.generation import _demografia_sem_sobrescrever_view

    local = {
        "pop_total_2022": 9000,
        "pop_total_2000": 9800,  # a view não tem 2000: o local preenche
        "cres_pop": -5.3,
        "porte_mun": "baixo porte",
        "media_porte": -1.2,
        "comparar_pop_porte": "inferior à",
    }
    view = {
        "pop_total_2022": 9000,
        "cres_pop": 5.26,
        "cres_pop_analise": "uma redução",
        "porte_mun": "pequeno porte",
        "media_porte": 1.2,
        "comparar_pop_porte": "similar à",
    }

    linha = dict(view)
    linha.update(_demografia_sem_sobrescrever_view(local, view))

    assert linha["cres_pop"] == 5.26
    assert linha["porte_mun"] == "pequeno porte"
    assert linha["media_porte"] == 1.2
    assert linha["pop_total_2000"] == 9800
    assert linha["comparar_pop_porte"] == "similar à"


def test_sem_view_calculo_local_vale_inteiro():
    # Fallback CSV (PR #91): sem linha da view, o banco continua completando o CSV.
    from services.generation import _demografia_sem_sobrescrever_view

    local = {"cres_pop": -5.3, "porte_mun": "baixo porte"}
    assert _demografia_sem_sobrescrever_view(local, None) == local


def test_cor_raca_da_view_nao_e_sobrescrita_pelo_ranking_local():
    # Regressão: o ranking local de cor/raça sobrescrevia a view e o Doc saía
    # "A população indigena representa..." onde a view traz a classe certa.
    from services.generation import _cor_raca_sem_sobrescrever_view

    local = {
        "cor_quar_class": "indigena",
        "cor_quar_per": 0.1,
        "cor_pri_class": "pardas",
        "cat_etaria_maior": "20 a 29 anos",
    }
    view = {
        "cor_quar_class": "amarela",
        "cor_quar_per": 0.5,
        "cat_etaria_maior": "0 a 14 anos",
    }

    linha = dict(view)
    linha.update(_cor_raca_sem_sobrescrever_view(local, view))

    assert linha["cor_quar_class"] == "amarela"
    assert linha["cor_quar_per"] == 0.5
    # A view não tem: o local preenche.
    assert linha["cor_pri_class"] == "pardas"
    # Faixa etária segue vindo do local (casa com a legenda do gráfico).
    assert linha["cat_etaria_maior"] == "20 a 29 anos"
    assert _cor_raca_sem_sobrescrever_view(local, None) == local


def test_indigena_da_view_nao_e_sobrescrita_pelo_calculo_local():
    # Regressão: buscar_populacao_indigena sobrescrevia a view e o Doc saía
    # "a de 80 ou mais anos" (o Doc acrescentava "anos" a "30 a 39") e
    # "21,50%" onde a view tem 21,55%.
    from services.generation import _indigena_sem_sobrescrever_view

    local = {
        "pop_total_indigena": 470,
        "cat_etaria_ind_pri": "30 a 39",
        "pop_etaria_ind_pri": 99,
        "cat_etaria_ind_seg": "80 ou mais",
        "var_pop_ind_abs": 21.5,
        "var_pop_ind_analise": "aumento",
    }
    view = {
        "cat_etaria_ind_pri": "30 a 39 anos",
        "pop_etaria_ind_pri": 99,
        "cat_etaria_ind_seg": "80 anos ou mais",
        "var_pop_ind_abs": "21.55",
        "var_pop_ind_analise": "estabilidade",
    }

    linha = dict(view)
    linha.update(_indigena_sem_sobrescrever_view(local, view))

    assert linha["cat_etaria_ind_pri"] == "30 a 39 anos"
    assert linha["cat_etaria_ind_seg"] == "80 anos ou mais"
    assert linha["var_pop_ind_abs"] == "21.55"
    assert linha["var_pop_ind_analise"] == "estabilidade"
    # A view não tem: o local preenche.
    assert linha["pop_total_indigena"] == 470
    assert _indigena_sem_sobrescrever_view(local, None) == local


def test_cor_raca_com_pessoas_e_percentual_zero_mostra_casas_decimais():
    # Regressão: com 1 pessoa em 20.953 habitantes a view guarda 0,00 e o Doc
    # saía "e a indígena, 0% (1)" (Coreaú, CE; 9 municípios em 29/09/2026).
    # O Time Dados pediu o valor com as casas decimais: "0,005%".
    from decimal import Decimal

    from services.generation import _percentuais_pequenos_com_casas

    linha = {
        "pop_total_2022": 20953,
        "cor_pri_pop": 14000, "cor_pri_per": Decimal("66.82"),
        "cor_quar_pop": 2, "cor_quar_per": Decimal("0.01"),
        "cor_quin_class": "indígena", "cor_quin_pop": 1, "cor_quin_per": Decimal("0.00"),
    }
    _percentuais_pequenos_com_casas(linha)

    assert linha["cor_quin_per"] == "0,005"
    # Percentual que não arredonda para zero fica como está.
    assert linha["cor_quar_per"] == Decimal("0.01")
    assert linha["cor_pri_per"] == Decimal("66.82")


def test_quilombola_com_pessoas_e_percentual_zero_mostra_casas_decimais():
    # Fortaleza saía "representava 0% da população total (39)".
    from decimal import Decimal

    from services.generation import _percentuais_pequenos_com_casas

    linha = {"pop_total_2022": 2428708, "pop_qui": 39, "pop_qui_per": Decimal("0.00")}
    _percentuais_pequenos_com_casas(linha)
    assert linha["pop_qui_per"] == "0,002"


def test_percentual_ate_primeiro_algarismo():
    from services.generation import _percentual_ate_primeiro_algarismo

    assert _percentual_ate_primeiro_algarismo(1, 20953) == "0,005"  # 0,00477
    assert _percentual_ate_primeiro_algarismo(1, 29412) == "0,003"  # 0,00340
    assert _percentual_ate_primeiro_algarismo(7, 866300) == "0,0008"  # 0,00081
    # O arredondamento que sobe uma casa não deixa zero sobrando no fim.
    assert _percentual_ate_primeiro_algarismo(96, 10_000_000) == "0,001"  # 0,00096


def test_percentuais_sem_pessoas_mantem_0():
    # Com 0 pessoas o "0%" está certo (São Pedro, RN: "e a indígena, 0% (0)").
    from decimal import Decimal

    from services.generation import _percentuais_pequenos_com_casas

    linha = {
        "pop_total_2022": 6000,
        "cor_quin_pop": 0, "cor_quin_per": Decimal("0.00"),
        "pop_qui": 0, "pop_qui_per": Decimal("0.00"),
    }
    _percentuais_pequenos_com_casas(linha)
    assert linha["cor_quin_per"] == Decimal("0.00")
    assert linha["pop_qui_per"] == Decimal("0.00")
