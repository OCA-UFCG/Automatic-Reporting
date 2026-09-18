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
        ("80+ anos", 5, 5, 9),  # menor faixa: 10
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
    assert resultado["cat_etaria_menor"] == "80+ anos"
    assert resultado["etaria_menor"] == 10


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
