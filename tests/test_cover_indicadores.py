from utils.cover import (
    INDICADORES_POR_MACROTEMA,
    montar_indicadores_macrotema,
    montar_score_macrotema,
)

# Contexto sintético no formato do que `buscar_indicadores_municipio` devolve
# (colunas de relatorios_auto.vw_indicadores). Nenhum teste aqui toca o banco.
CONTEXTO = {
    "idhm_2010": "0.770",
    "renda_per_capita_2010": "630.03",
    "indice_gini_2010": "0.58",
    "nao_alfabetizados_15_mais": 26939,
    "reducao_nao_alfabetizados_2010_2022": 7351,
    "sem_instrucao_fund_incomp_per": "46.50",
    "fund_comp_medio_incomp_per": "13.73",
    "medio_comp_superior_incomp_per": "27.06",
    "superior_completo_per": "12.70",
    "pop_quilombola_2022": 0,
    "pop_quilombola_per_2022": "0.00",
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
