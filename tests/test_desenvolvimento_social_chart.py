from pathlib import Path

import pytest

from plotting.desenvolvimento_social import gerar_grafico_de_desenvolvimento_social


def test_gera_grafico_com_serie_historica_do_idhm(tmp_path: Path):
    cidade = {"idhm_1991": 0.312, "idhm_2000": 0.451, "idhm_2010": 0.561}

    arquivo = gerar_grafico_de_desenvolvimento_social(
        cidade, tmp_path, "canapi_al"
    )

    assert arquivo == "grafico_de_desenvolvimento_social_canapi_al.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_exige_ao_menos_um_ano_de_idhm(tmp_path: Path):
    with pytest.raises(ValueError, match="Dados históricos"):
        gerar_grafico_de_desenvolvimento_social({}, tmp_path, "sem_dados")
