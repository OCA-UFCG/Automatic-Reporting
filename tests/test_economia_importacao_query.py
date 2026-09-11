from utils.queries import economia_importacao


def test_buscar_linhas_importacao_mapeia_colunas_da_consulta(monkeypatch):
    linhas_banco = [
        (2026, "06", "junho", "País A", "Seção X", "Produto 1", 1000.0, 40000.0),
    ]
    monkeypatch.setattr(
        economia_importacao, "executar_query", lambda *args, **kwargs: linhas_banco
    )

    linhas = economia_importacao.buscar_linhas_importacao("Fortaleza", "CE")

    assert linhas == [
        {
            "co_ano": 2026,
            "co_mes": "06",
            "desc_mes": "junho",
            "desc_pais_portugues": "País A",
            "desc_secao": "Seção X",
            "desc_sh4": "Produto 1",
            "kg_liquido": 1000.0,
            "vl_fob": 40000.0,
        }
    ]


def test_processar_importacao_retorna_none_sem_dados():
    assert economia_importacao.processar_importacao([]) is None


def test_processar_importacao_calcula_resumo_paises_secoes_e_produtos_do_ultimo_mes():
    linhas = [
        {"co_ano": 2026, "co_mes": "06", "desc_mes": "junho", "desc_pais_portugues": "País A", "desc_secao": "Seção X", "desc_sh4": "Produto 1", "kg_liquido": 1000.0, "vl_fob": 40000.0},
        {"co_ano": 2026, "co_mes": "06", "desc_mes": "junho", "desc_pais_portugues": "País A", "desc_secao": "Seção Y", "desc_sh4": "Produto 2", "kg_liquido": 200.0, "vl_fob": 20000.0},
        {"co_ano": 2026, "co_mes": "06", "desc_mes": "junho", "desc_pais_portugues": "País B", "desc_secao": "Seção X", "desc_sh4": "Produto 1", "kg_liquido": 300.0, "vl_fob": 15000.0},
        {"co_ano": 2026, "co_mes": "06", "desc_mes": "junho", "desc_pais_portugues": "País C", "desc_secao": "Seção Y", "desc_sh4": "Produto 3", "kg_liquido": 50.0, "vl_fob": 8000.0},
        {"co_ano": 2026, "co_mes": "06", "desc_mes": "junho", "desc_pais_portugues": "País D", "desc_secao": "Seção Y", "desc_sh4": "Produto 3", "kg_liquido": 20.0, "vl_fob": 3000.0},
        {"co_ano": 2026, "co_mes": "06", "desc_mes": "junho", "desc_pais_portugues": "País E", "desc_secao": "Seção X", "desc_sh4": "Produto 1", "kg_liquido": 10.0, "vl_fob": 1000.0},
    ]

    dados = economia_importacao.processar_importacao(linhas)

    assert dados["ultimo_mes_ano"] == "junho de 2026"
    assert dados["ultimo_jun"] == 2026

    assert dados["fob_importado_ultimo"] == 87.0
    assert dados["fob_importado_ultimo_unid"] == "mil"
    assert round(dados["kg_importado_ultimo"], 2) == 1.58
    assert dados["kg_importado_ultimo_unid"] == "mil"

    assert dados["pais_importado1"] == "País A"
    assert dados["valor_pais_importado1"] == 60.0
    assert dados["valor_pais_importado_unid1"] == "mil"
    assert dados["pais_importado2"] == "País B"
    assert dados["valor_pais_importado2"] == 15.0
    assert dados["pais_importado3"] == "País C"
    assert dados["valor_pais_importado3"] == 8.0
    assert dados["pais_importado4"] == "País D"
    assert dados["valor_pais_importado4"] == 3.0
    assert "pais_importado5" not in dados

    assert dados["secao_produtos1"] == "Seção X"
    assert dados["valor_secao_importado1"] == 56.0
    assert dados["secao_produtos2"] == "Seção Y"
    assert dados["valor_secao_importado2"] == 31.0

    assert dados["produto_importado1"] == "Produto 1"
    assert dados["valor_produto_importado1"] == 56.0
    assert round(dados["kg_importado_produto1"], 2) == 1.31
    assert dados["kg_importado_produtounid1"] == "mil"
    assert dados["produto_importado_kg1"] == "Produto 1"

    assert dados["produto_importado2"] == "Produto 2"
    assert dados["valor_produto_importado2"] == 20.0
    assert dados["kg_importado_produto2"] == 200.0
    assert dados["produto_importadokg2"] == "Produto 2"


def test_processar_importacao_expoe_top10_paises_bruto_para_o_grafico():
    linhas = [
        {"co_ano": 2026, "co_mes": "06", "desc_mes": "junho", "desc_pais_portugues": f"País {i}", "desc_secao": "Seção X", "desc_sh4": "Produto 1", "kg_liquido": 1.0, "vl_fob": float(1200 - i * 100)}
        for i in range(12)
    ]

    dados = economia_importacao.processar_importacao(linhas)

    paises = dados["importacao_paises"]
    assert len(paises) == 10
    assert paises[0] == ("País 0", 1200.0)
    assert paises[-1] == ("País 9", 300.0)
    assert paises == sorted(paises, key=lambda item: item[1], reverse=True)


def test_processar_importacao_compara_valor_medio_por_kg_entre_janeiro_e_junho():
    linhas = [
        {"co_ano": 2026, "co_mes": "01", "desc_mes": "janeiro", "desc_pais_portugues": "País A", "desc_secao": "Seção X", "desc_sh4": "Produto 1", "kg_liquido": 500.0, "vl_fob": 10000.0},
        {"co_ano": 2026, "co_mes": "06", "desc_mes": "junho", "desc_pais_portugues": "País A", "desc_secao": "Seção X", "desc_sh4": "Produto 1", "kg_liquido": 1580.0, "vl_fob": 87000.0},
    ]

    dados = economia_importacao.processar_importacao(linhas)

    assert dados["valormedio_importado_jan"] == 20.0
    assert dados["valormedio_importado_janunid"] == ""
    assert round(dados["valormedio_importado_jun"], 2) == 55.06
    assert dados["analise_importado_janjun"] == "aumento"
