from pathlib import Path

import pytest

from plotting.economia_renda import gerar_grafico_pib


def test_gera_grafico_com_serie_do_banco(tmp_path: Path):
    cidade = {
        "pib_serie": [
            {"ano": 2010, "pib_total": 166512845},
            {"ano": 2020, "pib_total": 8299245300},
            {"ano": 2023, "pib_total": 12945093200},
        ]
    }

    arquivo = gerar_grafico_pib(cidade, tmp_path, "campina_grande_pb")

    assert arquivo == "grafico_pib_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_exige_serie_anual():
    with pytest.raises(ValueError, match="Dados anuais"):
        gerar_grafico_pib({}, Path("/tmp"), "sem_dados")
