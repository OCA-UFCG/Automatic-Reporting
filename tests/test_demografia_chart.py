from pathlib import Path

import pytest

from plotting.demografia import (
    gerar_grafico_composicao_cor_raca,
    gerar_grafico_faixa_etaria_e_sexo,
    gerar_grafico_visao_historica_populacao,
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


def test_grafico_visao_historica_populacao_exige_dados():
    with pytest.raises(ValueError, match="não disponíveis"):
        gerar_grafico_visao_historica_populacao({}, Path("/tmp"), "sem_dados")
