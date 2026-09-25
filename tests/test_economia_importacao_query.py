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

    # nomes saem em minúscula: o Doc usa todos no meio da frase
    assert dados["secao_importado1"] == "seção x"
    assert dados["valor_secao_importado1"] == 56.0
    assert dados["secao_importado2"] == "seção y"
    assert dados["valor_secao_importado2"] == 31.0

    assert dados["produto_importado1"] == "produto 1"
    assert dados["valor_produto_importado1"] == 56.0
    assert round(dados["kg_importado_produto1"], 2) == 1.31
    assert dados["kg_importado_produtounid1"] == "mil"
    assert dados["produto_importado_kg1"] == "produto 1"

    assert dados["produto_importado2"] == "produto 2"
    assert dados["valor_produto_importado2"] == 20.0
    assert dados["kg_importado_produto2"] == 200.0
    assert dados["produto_importado_kg2"] == "produto 2"


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


def test_processar_importacao_zera_slots_sem_dado_no_ultimo_mes():
    """Slot vazio precisa sair 0/"": generation.py mescla este dict por cima da
    linha da mv_perfil_economia, que traz esses mesmos campos de outro recorte."""
    linhas = [
        {"co_ano": 2026, "co_mes": "08", "desc_mes": "agosto", "desc_pais_portugues": "País A", "desc_secao": "Seção X", "desc_sh4": "Produto 1", "kg_liquido": 10.0, "vl_fob": 500.0},
    ]

    dados = economia_importacao.processar_importacao(linhas)

    for posicao in (2, 3, 4):
        assert dados[f"pais_importado{posicao}"] == ""
        assert dados[f"valor_pais_importado{posicao}"] == 0
    assert dados["secao_importado2"] == ""
    assert dados["valor_secao_importado2"] == 0
    assert dados["produto_importado2"] == ""
    assert dados["produto_importado_kg2"] == ""


def test_processar_importacao_nao_vaza_kg_quando_produto_top_fob_nao_tem_peso():
    """O produto #1 em valor pode não ter peso registrado: ele completa a segunda
    posição com 0, sem deixar $kg_importado_produto* cru no relatório."""
    linhas = [
        {"co_ano": 2026, "co_mes": "08", "desc_mes": "agosto", "desc_pais_portugues": "País A", "desc_secao": "Seção X", "desc_sh4": "Produto 1", "kg_liquido": None, "vl_fob": 5000.0},
        {"co_ano": 2026, "co_mes": "08", "desc_mes": "agosto", "desc_pais_portugues": "País B", "desc_secao": "Seção X", "desc_sh4": "Produto 2", "kg_liquido": 100.0, "vl_fob": 1000.0},
    ]

    dados = economia_importacao.processar_importacao(linhas)

    assert dados["produto_importado_kg1"] == "produto 2"
    assert dados["kg_importado_produto1"] == 100.0
    assert dados["produto_importado_kg2"] == "produto 1"
    assert dados["kg_importado_produto2"] == 0
    assert dados["kg_importado_produtounid2"] == ""


def _linha_importacao(produto, kg, fob, pais="País A"):
    return {
        "co_ano": 2026, "co_mes": "08", "desc_mes": "agosto",
        "desc_pais_portugues": pais, "desc_secao": "Seção X",
        "desc_sh4": produto, "kg_liquido": kg, "vl_fob": fob,
    }


def test_processar_importacao_ordena_os_pesos_por_kg_e_nao_por_valor():
    """Davinópolis/MA: pneumáticos (223 mil kg) antes de queijos (216 mil kg),
    embora queijos tenham o maior valor."""
    linhas = [
        _linha_importacao("Queijos e requeijão", 216_013.0, 1_090_000.0),
        _linha_importacao("Pneumáticos novos, de borracha", 223_517.0, 501_300.0),
    ]

    dados = economia_importacao.processar_importacao(linhas)

    assert dados["produto_importado1"] == "queijos e requeijão"
    assert dados["produto_importado_kg1"] == "pneumáticos novos, de borracha"
    assert dados["kg_importado_produto1"] == 223.517
    assert dados["produto_importado_kg2"] == "queijos e requeijão"


def test_processar_importacao_com_um_produto_usa_o_peso_dele():
    """"O único produto… correspondentes a $kg_importado_produto1 kg"."""
    linhas = [
        _linha_importacao("Produto com valor", 10.0, 1000.0),
        _linha_importacao("Produto sem valor", 500.0, None),
    ]

    dados = economia_importacao.processar_importacao(linhas)

    assert dados["produto_importado1"] == "produto com valor"
    assert dados["produto_importado_kg1"] == "produto com valor"
    assert dados["kg_importado_produto1"] == 10.0


def test_processar_importacao_concorda_unidade_e_poe_de_no_peso():
    """"US$ 1,70 milhão" e "34,47 milhões de kg"."""
    linhas = [_linha_importacao("Produto 1", 34_470_000.0, 1_700_000.0)]

    dados = economia_importacao.processar_importacao(linhas)

    assert dados["fob_importado_ultimo_unid"] == "milhão"
    assert dados["valor_pais_importado_unid1"] == "milhão"
    assert dados["kg_importado_ultimo_unid"] == "milhões de"
    assert dados["kg_importado_produtounid1"] == "milhões de"
