from pathlib import Path

import pytest

from plotting.demografia import (
    gerar_grafico_composicao_cor_raca,
    gerar_grafico_faixa_etaria_e_sexo,
)


def _cidade_cor_raca():
    return {
        "pop_branca": 160000,
        "pop_preta": 80000,
        "pop_parda": 350000,
        "pop_amarela": 7700,
        "pop_indigena": 3200,
    }


def _cidade_faixa_etaria():
    return {
        "faixas_etarias_sexo": [
            {"faixa": "0-4", "mulheres": 1200, "homens": 1300},
            {"faixa": "5-9", "mulheres": 1400, "homens": 1500},
        ]
    }


def test_gera_grafico_composicao_cor_raca(tmp_path: Path):
    arquivo = gerar_grafico_composicao_cor_raca(
        _cidade_cor_raca(), tmp_path, "campina_grande_pb"
    )

    assert arquivo == "grafico_composicao_cor_raca_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_composicao_cor_raca_exige_dados(tmp_path: Path):
    with pytest.raises(ValueError, match="Dados de composição por cor ou raça"):
        gerar_grafico_composicao_cor_raca({}, tmp_path, "sem_dados")


def test_gera_grafico_faixa_etaria_e_sexo(tmp_path: Path):
    arquivo = gerar_grafico_faixa_etaria_e_sexo(
        _cidade_faixa_etaria(), tmp_path, "campina_grande_pb"
    )

    assert arquivo == "grafico_faixa_etaria_e_sexo_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_faixa_etaria_e_sexo_exige_dados(tmp_path: Path):
    with pytest.raises(ValueError, match="Dados por faixa etária e sexo"):
        gerar_grafico_faixa_etaria_e_sexo({}, tmp_path, "sem_dados")
