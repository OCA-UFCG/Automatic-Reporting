from utils.cover import (
    INDICADORES_POR_MACROTEMA,
    montar_indicadores_macrotema,
    montar_score_macrotema,
)

# Contexto sintético no formato do que `buscar_indicadores_municipio` devolve
# (colunas de relatorios_auto.vw_indicadores). Nenhum teste aqui toca o banco.
CONTEXTO = {
    "valor_idhm": "0.770",
    "valor_renda_capita": "630.03",
    "valor_gini": "0.58",
    "nao_alfabetizados_15_mais": 26939,
    "reducao_nao_alfabetizados_2010_2022": 7351,
    "sem_instrucao_fund_incomp_per": "46.50",
    "fund_comp_medio_incomp_per": "13.73",
    "medio_comp_superior_incomp_per": "27.06",
    "superior_completo_per": "12.70",
    "pop_quilombola_2022": 0,
    "indice_suscetibilidade_escassez_hidrica": "0.5",
    "qtd_usinas": 1,
    "potencia_renovavel": "0",
    "potencia_nao_renovavel": "169080.00",
    "aumento_domicilios_rede_esgoto_2010_2022": 38621,
}


def _por_nome(indicadores: list[dict]) -> dict[str, str]:
    return {item["nome"]: item["valor"] for item in indicadores}


def test_indicadores_usam_valores_do_contexto():
    valores = _por_nome(
        montar_indicadores_macrotema("desenvolvimento-social", CONTEXTO)
    )

    assert valores["IDHM"] == "0,77"
    assert valores["Renda per capita"] == "R$ 630,03"
    assert valores["Índice de Gini"] == "0,58"


def test_desenvolvimento_social_mostra_os_subindices_do_idhm():
    # `valor_idhm_educacao`, `valor_idhm_longevidade` e `valor_idhm_renda` são
    # colunas novas em vw_indicadores; os cards de IDHM/renda/Gini também
    # migraram de `idhm_2010`/`renda_per_capita_2010`/`indice_gini_2010`
    # (colunas que não existem mais na view) para `valor_idhm`/
    # `valor_renda_capita`/`valor_gini`.
    contexto = {
        **CONTEXTO,
        "valor_idhm_educacao": "0.458",
        "valor_idhm_longevidade": "0.843",
        "valor_idhm_renda": "0.719",
    }

    valores = _por_nome(
        montar_indicadores_macrotema("desenvolvimento-social", contexto)
    )

    assert valores["IDHM Educação"] == "0,458"
    assert valores["IDHM Longevidade"] == "0,843"
    assert valores["IDHM Renda"] == "0,719"


def test_economia_renda_nao_mostra_renda_capita_nem_gini():
    # O Doc de economia pede só 6 indicadores (PIB, PIB per capita, Carga
    # tributária, Exportação, Importação, Balança comercial); Renda per
    # capita e Índice de Gini pertencem ao card de desenvolvimento-social,
    # não ao de economia-renda.
    valores = _por_nome(montar_indicadores_macrotema("economia-renda", CONTEXTO))

    assert "Renda per capita" not in valores
    assert "Índice de Gini" not in valores


def test_economia_renda_mostra_os_6_indicadores_novos_da_view():
    contexto = {
        **CONTEXTO,
        "valor_pib": "12908743000",
        "valor_pib_capita": "30780.61",
        "valor_exportacao": "3560041.00",
        "valor_importacao": "10865532.00",
        "valor_balanca": "-7305491.00",
        "valor_carga_tributaria": "277942183.71",
        "fonte_exportacao": "SECEX (julho de 2026)",
        "fonte_importacao": "SECEX (julho de 2026)",
        "fonte_balanca": "SECEX (julho de 2026)",
    }
    valores = _por_nome(montar_indicadores_macrotema("economia-renda", contexto))

    assert valores["PIB"] == "R$ 12.908.743.000"
    assert valores["PIB per capita"] == "R$ 30.780,61"
    assert valores["Exportações"] == "US$ 3.560.041"
    assert valores["Importações"] == "US$ 10.865.532"
    assert valores["Balança comercial"] == "US$ -7.305.491"
    assert valores["Receita tributária municipal"] == "R$ 277.942.183,71"


def test_fonte_coluna_le_o_mes_de_referencia_direto_da_view():
    # O mês de referência do SECEX muda a cada carga; a fonte desses 3 cards
    # vem de "fonte_<coluna>" na view em vez de um texto fixo que ficaria
    # desatualizado no relatório do mês seguinte.
    contexto = {**CONTEXTO, "valor_exportacao": "1", "fonte_exportacao": "SECEX (março de 2027)"}
    fontes = {item["nome"]: item["fonte"] for item in montar_indicadores_macrotema("economia-renda", contexto)}

    assert fontes["Exportações"] == "SECEX (março de 2027)"


def test_fonte_coluna_cai_no_texto_fixo_quando_a_view_nao_traz_o_mes():
    contexto = {**CONTEXTO, "valor_exportacao": "1"}
    fontes = {item["nome"]: item["fonte"] for item in montar_indicadores_macrotema("economia-renda", contexto)}

    assert fontes["Exportações"] == "SECEX"


def test_percentuais_e_contagens_sao_formatados_em_ptbr():
    valores = _por_nome(montar_indicadores_macrotema("educacao", CONTEXTO))

    assert valores["Pessoas não alfabetizadas (15 anos ou mais)"] == "26.939"
    assert valores["Sem instrução ou fundamental incompleto"] == "46,5%"
    assert valores["Superior completo"] == "12,7%"


def test_indicador_sem_valor_no_banco_e_omitido():
    # meio-ambiente é o macrotema com colunas incompletas na view
    # (area_suscetivel_desertificacao cobre ~2/3 dos municípios).
    indicadores = montar_indicadores_macrotema(
        "meio-ambiente",
        {"qtd_unidades_conservacao": 3, "area_suscetivel_desertificacao": None},
    )

    nomes = {item["nome"] for item in indicadores}
    assert "Unidades de conservação" in nomes
    assert "Área suscetível à desertificação" not in nomes
    assert all(item["valor"] for item in indicadores)


def test_sem_contexto_nao_inventa_indicador():
    assert montar_indicadores_macrotema("saneamento") == []
    assert montar_indicadores_macrotema("saneamento", {}) == []


def test_saude_nao_tem_indicadores_na_view():
    # vw_indicadores não traz nenhuma coluna de saúde; o bloco simplesmente não
    # é renderizado em vez de exibir score fictício (era "4/5", "2/5"...).
    assert "saude" not in INDICADORES_POR_MACROTEMA
    assert montar_indicadores_macrotema("saude", CONTEXTO) == []


def test_demografia_mostra_todos_os_bignumbers_da_view():
    # `populacao_residente_2022`, `pop_masc_2022`, `pop_feminina_2022` e
    # `pop_indigena_2022` chegaram na view depois e nunca tinham sido cadastrados
    # como card; `pop_quilombola_per_2022` era um card cadastrado para uma coluna
    # que não existe na view (sempre omitido) — corrigido para `pop_qui_per`,
    # que chega no contexto mesclado via buscar_populacao_quilombola.
    contexto = {
        **CONTEXTO,
        "populacao_residente_2022": 45210,
        "pop_masc_2022": 22300,
        "pop_feminina_2022": 22910,
        "pop_indigena_2022": 812,
        "pop_rua_2022": 15,
        "pop_qui_per": "3.20",
    }

    valores = _por_nome(montar_indicadores_macrotema("demografia", contexto))

    assert valores["População residente"] == "45.210"
    assert valores["População masculina"] == "22.300"
    assert valores["População feminina"] == "22.910"
    assert valores["População indígena"] == "812"
    assert valores["População em situação de rua"] == "15"
    assert valores["População quilombola"] == "0"
    assert valores["Participação da população quilombola"] == "3,2%"


def test_indicadores_diferem_entre_macrotemas():
    nomes_hidraulica = {
        item["nome"] for item in montar_indicadores_macrotema("hidraulica", CONTEXTO)
    }
    nomes_educacao = {
        item["nome"] for item in montar_indicadores_macrotema("educacao", CONTEXTO)
    }

    assert nomes_hidraulica
    assert nomes_educacao
    assert nomes_hidraulica.isdisjoint(nomes_educacao)


def test_icone_do_macrotema_e_usado_quando_o_indicador_nao_define_um():
    indicadores = montar_indicadores_macrotema(
        "saneamento", CONTEXTO, macrotema_icone="wrench"
    )

    assert indicadores
    assert all(item["icone"] == "wrench" for item in indicadores)


def test_todas_as_colunas_do_catalogo_tem_rotulo_e_fonte():
    for specs in INDICADORES_POR_MACROTEMA.values():
        for spec in specs:
            assert spec["coluna"]
            assert spec["nome"]
            assert spec["fonte"]


def test_score_usa_a_linha_do_tema_correspondente():
    score_demografia = montar_score_macrotema({"score_geral": "4,20"})
    score_saude = montar_score_macrotema({"score_geral": "1,80"})

    assert score_demografia["valor"] == "4,20"
    assert score_saude["valor"] == "1,80"


def test_score_usa_fallback_quando_coluna_ausente():
    score = montar_score_macrotema({})

    assert score["valor"] == "3,66"
    assert score["maximo"] == "5"
