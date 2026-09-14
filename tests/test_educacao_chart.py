from pathlib import Path

import pytest

from plotting.educacao import (
    gerar_grafico_cor_faixa_etaria,
    gerar_grafico_nivel_instrucao,
)

FAIXAS = ["15_a_19", "20_a_29", "30_a_39", "40_a_49", "50_a_59", "mais60"]
CORES = ["amarela", "branca", "indigena", "parda", "preta"]

NIVEIS_INSTRUCAO = ["pri_nivel", "seg_nivel", "ter_nivel", "quar_nivel"]


def _cidade_completa():
    return {
        f"taxa_{faixa}_{cor}": 5.0
        for faixa in FAIXAS
        for cor in CORES
    }


def _cidade_com_niveis_instrucao():
    return {
        "pri_nivel_classe": "Fundamental incompleto",
        "pri_nivel_per": 44.63,
        "pri_nivel_pop": 15410166,
        "seg_nivel_classe": "Fundamental completo",
        "seg_nivel_per": 12.79,
        "seg_nivel_pop": 4415858,
        "ter_nivel_classe": "Médio completo",
        "ter_nivel_per": 29.56,
        "ter_nivel_pop": 10208364,
        "quar_nivel_classe": "Superior completo",
        "quar_nivel_per": 13.02,
        "quar_nivel_pop": 4494747,
    }


def test_gera_grafico_com_todas_as_colunas(tmp_path: Path):
    arquivo = gerar_grafico_cor_faixa_etaria(
        _cidade_completa(), tmp_path, "campina_grande_pb"
    )

    assert arquivo == "grafico_cor_faixa_etaria_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_exige_todas_as_colunas(tmp_path: Path):
    with pytest.raises(ValueError, match="Colunas necessárias ausentes"):
        gerar_grafico_cor_faixa_etaria({}, tmp_path, "sem_dados")


def test_gera_grafico_nivel_instrucao_com_todas_as_colunas(tmp_path: Path):
    arquivo = gerar_grafico_nivel_instrucao(
        _cidade_com_niveis_instrucao(), tmp_path, "campina_grande_pb"
    )

    assert arquivo == "grafico_nivel_instrucao_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_nivel_instrucao_exige_todas_as_colunas(tmp_path: Path):
    with pytest.raises(ValueError, match="Colunas necessárias ausentes"):
        gerar_grafico_nivel_instrucao({}, tmp_path, "sem_dados")


def test_grafico_nivel_instrucao_exige_alguma_populacao(tmp_path: Path):
    cidade = {
        f"{prefixo}_{sufixo}": 0
        for prefixo in NIVEIS_INSTRUCAO
        for sufixo in ("classe", "per", "pop")
    }

    with pytest.raises(ValueError, match="não disponíveis"):
        gerar_grafico_nivel_instrucao(cidade, tmp_path, "sem_dados")
