from pathlib import Path

import pytest

from plotting.meio_ambiente import gerar_grafico_aridez


def test_gera_grafico_de_aridez(tmp_path: Path):
    cidade = {
        "area_arida2021_per": 0.6,
        "area_semiarida2021_per": 49.4,
        "area_subumida2021_per": 14.7,
        "area_umida2021_per": 34.7,
    }

    arquivo = gerar_grafico_aridez(cidade, tmp_path, "cidade_teste")

    assert arquivo == "grafico_aridez_cidade_teste.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_ignora_categoria_sem_dado(tmp_path: Path):
    cidade = {
        "area_semiarida2021_per": 80.0,
        "area_umida2021_per": 20.0,
    }

    arquivo = gerar_grafico_aridez(cidade, tmp_path, "cidade_parcial")

    assert (tmp_path / arquivo).is_file()


def test_grafico_exige_dados(tmp_path: Path):
    with pytest.raises(ValueError, match="não disponíveis"):
        gerar_grafico_aridez({}, tmp_path, "sem_dados")
