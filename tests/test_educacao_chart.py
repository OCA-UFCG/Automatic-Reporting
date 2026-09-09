from pathlib import Path

import pytest

from plotting.educacao import gerar_grafico_cor_faixa_etaria

FAIXAS = ["15_a_19", "20_a_29", "30_a_39", "40_a_49", "50_a_59", "mais60"]
CORES = ["amarela", "branca", "indigena", "parda", "preta"]


def _cidade_completa():
    return {
        f"taxa_{faixa}_{cor}": 5.0
        for faixa in FAIXAS
        for cor in CORES
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
