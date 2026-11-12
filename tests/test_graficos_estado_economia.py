"""Gráficos de Economia e Renda no relatório por estado (12/11/2026): os adaptadores
transformam a linha `uf_*` da est_economia (valores escalados, listas de países,
saldos por mês) no que as funções de plotting/economia_renda.py leem. Nenhum teste
toca o banco: a linha é um recorte da Paraíba."""

from decimal import Decimal
from pathlib import Path

import pytest

from services.graficos_estado import gerar_graficos_do_estado
from services.graficos_estado_economia import (
    balanca_do_estado,
    exportacao_paises_do_estado,
    importacao_paises_do_estado,
    pib_serie_do_estado,
    vab_setores_do_estado,
    valor_absoluto_do_estado,
)


def _linha_economia_paraiba() -> dict:
    paises = [f"País {numero}" for numero in range(1, 13)]
    fob = [Decimal(1_000_000 * (13 - numero)) for numero in range(1, 13)]
    return {
        "uf_estado": "Paraíba",
        "uf_sigla_uf": "PB",
        "uf_pib_2023": Decimal("96.96"),
        "uf_pib_unid_2023": "bilhões",
        "uf_pib_2010": Decimal("33.52"),
        "uf_pib_unid_2010": "bilhões",
        "uf_pib_var_per_abs": Decimal("189.25"),
        "uf_setor2021_maior1": "de Serviços",
        "uf_valor_setor2021_maior1": Decimal("32.58"),
        "uf_setor2021_maior1unid": "bilhões",
        "uf_setor2021_maior2": "da Administração pública",
        "uf_valor_setor2021_maior2": Decimal("21.93"),
        "uf_setor2021_maior2unid": "bilhões",
        "uf_setor2021_maior3": "da Indústria",
        "uf_valor_setor2021_maior3": Decimal("10.07"),
        "uf_setor2021_maior3unid": "bilhões",
        "uf_setor2021_menor": "Agropecuária",
        "uf_valor_setor2021_menor": Decimal("3.19"),
        "uf_setor2021_menor_unid": "bilhões",
        "uf_importacao_pais_nome": paises,
        "uf_importacao_pais_fob": fob,
        "uf_exportacao_pais_nome": paises,
        "uf_exportacao_pais_fob": fob,
        "uf_balanca_saldo_mensal_01": Decimal("-38248761.00"),
        "uf_balanca_saldo_mensal_02": Decimal("-29066585.00"),
        "uf_balanca_saldo_mensal_09": None,
        "uf_fob_exportado_ultimo": Decimal("9.34"),
        "uf_fob_importado_ultimo": Decimal("26.89"),
    }


def test_valor_absoluto_desfaz_a_escala_da_matview():
    assert valor_absoluto_do_estado(Decimal("96.96"), "bilhões") == pytest.approx(96_960_000_000)
    assert valor_absoluto_do_estado(Decimal("1.40"), "milhão") == pytest.approx(1_400_000)
    assert valor_absoluto_do_estado(Decimal(12), "") == 12


def test_unidade_desconhecida_recusa_em_vez_de_encolher_o_valor():
    with pytest.raises(ValueError, match="'zilhões'"):
        valor_absoluto_do_estado(Decimal(1), "zilhões")


def test_pib_le_so_as_colunas_de_ano_em_ordem():
    serie = pib_serie_do_estado(_linha_economia_paraiba())["pib_serie"]

    assert [ponto["ano"] for ponto in serie] == [2010, 2023]
    assert serie[-1]["pib_total"] == pytest.approx(96_960_000_000)


def test_vab_tira_a_preposicao_do_nome_do_setor():
    setores = vab_setores_do_estado(_linha_economia_paraiba())["vab_setores_2021"]

    assert setores["servicos"] == pytest.approx(32_580_000_000)
    assert setores["adm_publica"] == pytest.approx(21_930_000_000)
    assert setores["agropecuaria"] == pytest.approx(3_190_000_000)


def test_vab_com_setor_faltando_recusa_o_grafico():
    linha = {**_linha_economia_paraiba(), "uf_setor2021_menor": None}

    with pytest.raises(ValueError, match="agropecuaria"):
        vab_setores_do_estado(linha)


def test_paises_mostram_10_na_importacao_e_4_na_exportacao_como_no_municipal():
    linha = _linha_economia_paraiba()

    importacao = importacao_paises_do_estado(linha)["importacao_paises"]
    exportacao = exportacao_paises_do_estado(linha)["exportacao_paises"]

    assert len(importacao) == 10
    assert exportacao == [
        ("País 1", Decimal(12_000_000)),
        ("País 2", Decimal(11_000_000)),
        ("País 3", Decimal(10_000_000)),
        ("País 4", Decimal(9_000_000)),
    ]


def test_balanca_pula_mes_sem_dado():
    balanca = balanca_do_estado(_linha_economia_paraiba())

    assert balanca["balanca_mensal"] == [("Jan", Decimal("-38248761.00")), ("Fev", Decimal("-29066585.00"))]
    assert balanca["fob_importado_ultimo"] == Decimal("26.89")


def test_gera_os_cinco_graficos_de_economia(tmp_path: Path):
    graficos = gerar_graficos_do_estado("economia-renda", _linha_economia_paraiba(), tmp_path, "estado_para_ba")

    assert list(graficos) == [
        "grafico_pib",
        "grafico_vab",
        "grafico_fob",
        "grafico_exportacao",
        "grafico_balanca",
    ]
    assert all((tmp_path / arquivo).is_file() for arquivo in graficos.values())
