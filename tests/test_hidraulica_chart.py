from pathlib import Path

import pytest

from plotting.hidraulica import gerar_grafico_tecnologias_acesso_agua


def test_gera_grafico_com_serie_do_banco(tmp_path: Path):
    cidade = {
        "tecnologias_acesso_agua_serie": [
            {"ano": 2010, "total": 439},
            {"ano": 2020, "total": 1841},
            {"ano": 2025, "total": 2038},
        ]
    }

    arquivo = gerar_grafico_tecnologias_acesso_agua(
        cidade, tmp_path, "campina_grande_pb"
    )

    assert arquivo == "grafico_tecnologias_acesso_agua_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_exige_serie_anual(tmp_path: Path):
    with pytest.raises(ValueError, match="Dados anuais"):
        gerar_grafico_tecnologias_acesso_agua({}, tmp_path, "sem_dados")
