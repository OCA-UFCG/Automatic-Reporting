from pathlib import Path

import pytest

from plotting.demografia import gerar_grafico_visao_historica_populacao


def test_gera_visao_historica_populacao(tmp_path: Path):
    # Campina Grande/PB (Censo 2000/2010/2022).
    cidade = {
        "pop_total_2000": 355331,
        "pop_total_2010": 385213,
        "pop_total_2022": 405072,
    }

    arquivo = gerar_grafico_visao_historica_populacao(cidade, tmp_path, "campina_grande_pb")

    assert arquivo == "grafico_visao_historica_populacao_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_usa_unidade_mil_para_municipios_pequenos(tmp_path: Path):
    # Canapi/AL: população na casa do milhar, não do milhão — dividir tudo
    # por 1_000_000 fazia toda barra arredondar para "0 Mi" (regressão).
    cidade = {
        "pop_total_2000": 7900,
        "pop_total_2010": 7600,
        "pop_total_2022": 6900,
    }

    arquivo = gerar_grafico_visao_historica_populacao(cidade, tmp_path, "canapi_al")

    assert (tmp_path / arquivo).is_file()


def test_grafico_exige_dados():
    with pytest.raises(ValueError, match="não disponíveis"):
        gerar_grafico_visao_historica_populacao({}, Path("/tmp"), "sem_dados")
