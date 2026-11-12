from pathlib import Path

import pytest

from plotting.meio_ambiente import (
    _percentuais_da_aridez,
    gerar_grafico_aridez,
    gerar_grafico_aridez_comparada,
)


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


def test_gera_grafico_com_area_sem_dados(tmp_path: Path):
    cidade = {
        "area_arida2021_per": 0.6,
        "area_semiarida2021_per": 49.4,
        "area_subumida2021_per": 14.7,
        "area_umida2021_per": 30.0,
        "area_sem_dados2021_per": 4.7,
    }

    arquivo = gerar_grafico_aridez(cidade, tmp_path, "cidade_sem_dados")

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


def _aridez_paraiba(**overrides: object) -> dict:
    """Paraíba na est_ambiente (sem o prefixo uf_): 1991 e 2021 válidos."""
    base = {
        "aridez_1991_valida": 1,
        "aridez_2021_valida": 1,
        "area_hiperarida1991_per": 0,
        "area_hiperarida2021_per": 0,
        "area_arida1991_per": 0,
        "area_arida2021_per": 0,
        "area_semiarida1991_per": 60.35,
        "area_semiarida2021_per": 83.62,
        "area_subumida1991_per": 26.44,
        "area_subumida2021_per": 8.38,
        "area_umida1991_per": 12.58,
        "area_umida2021_per": 7.38,
        "area_sem_dados1991_per": 0.62,
        "area_sem_dados2021_per": 0.62,
    }
    return {**base, **overrides}


def test_aridez_comparada_tira_classe_sem_area_nos_dois_anos():
    classes = _percentuais_da_aridez(_aridez_paraiba(), (1991, 2021))

    assert [rotulo for rotulo, _, _ in classes] == ["Semiárido", "Subúmido seco", "Úmido", "Sem dados"]
    assert classes[0][2] == {1991: 60.35, 2021: 83.62}


def test_aridez_comparada_mantem_classe_que_so_aparece_em_2021():
    # Bahia: árido 0% em 1991 e 1% em 2021 continua no gráfico.
    classes = _percentuais_da_aridez(_aridez_paraiba(area_arida2021_per=1.0), (1991, 2021))

    assert classes[0][0] == "Árido"


def test_gera_grafico_de_aridez_comparada(tmp_path: Path):
    arquivo = gerar_grafico_aridez_comparada(_aridez_paraiba(), tmp_path, "estado_para_ba")

    assert arquivo == "grafico_aridez_comparada_estado_para_ba.png"
    assert (tmp_path / arquivo).is_file()


def test_aridez_comparada_sem_1991_valido_sai_so_com_2021(tmp_path: Path):
    arquivo = gerar_grafico_aridez_comparada(_aridez_paraiba(aridez_1991_valida=0), tmp_path, "so_2021")

    assert (tmp_path / arquivo).is_file()


def test_aridez_comparada_exige_2021_valido(tmp_path: Path):
    with pytest.raises(ValueError, match="aridez_2021_valida=0"):
        gerar_grafico_aridez_comparada(_aridez_paraiba(aridez_2021_valida=0), tmp_path, "sem_2021")
