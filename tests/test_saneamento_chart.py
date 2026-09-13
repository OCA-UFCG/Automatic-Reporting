from pathlib import Path

import pytest

from plotting.saneamento import (
    gerar_grafico_esgotamento_sanitario,
    gerar_grafico_evolucao_coleta_lixo,
    gerar_grafico_evolucao_rede_geral_esgoto,
)


def test_gera_rosca_de_esgotamento(tmp_path: Path):
    # Campina Grande/PB (Censo 2022), a cidade da imagem do Doc.
    cidade = {
        "esg_total": 147149,
        "esg_rede_geral_ou_pluvial": 127454,
        "esg_fossa_septica_ou_fossa_filtro": 7799,
        "esg_fossa_rudimentar_ou_buraco": 6327,
        "esg_vala": 2060,
        "esg_rio_lago_corrego_ou_mar": 1913,
        "esg_outra_forma": 442,
        "esg_nao_tinham_banheiro": 1154,
    }

    arquivo = gerar_grafico_esgotamento_sanitario(cidade, tmp_path, "campina_grande_pb")

    assert arquivo == "grafico_esgotamento_sanitario_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_exige_dados(tmp_path: Path):
    with pytest.raises(ValueError, match="não disponíveis"):
        gerar_grafico_esgotamento_sanitario({"esg_total": 0}, tmp_path, "sem_dados")


def test_gera_evolucao_rede_geral_esgoto(tmp_path: Path):
    # Campina Grande/PB (vw_perfil_infraestrutura_municipal).
    cidade = {
        "esgoto_rede_2000": 68.4,
        "esgoto_rede_2010": 79.4,
        "esgoto_rede_2022": 86.6,
    }

    arquivo = gerar_grafico_evolucao_rede_geral_esgoto(cidade, tmp_path, "campina_grande_pb")

    assert arquivo == "grafico_evolucao_rede_geral_esgoto_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_evolucao_rede_geral_esgoto_exige_dados(tmp_path: Path):
    with pytest.raises(ValueError, match="não disponíveis"):
        gerar_grafico_evolucao_rede_geral_esgoto({}, tmp_path, "sem_dados")


def test_gera_evolucao_coleta_lixo(tmp_path: Path):
    cidade = {"coleta_2010": 94.8, "coleta_2022": 97.5}

    arquivo = gerar_grafico_evolucao_coleta_lixo(cidade, tmp_path, "campina_grande_pb")

    assert arquivo == "grafico_evolucao_coleta_lixo_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_evolucao_coleta_lixo_exige_dados(tmp_path: Path):
    with pytest.raises(ValueError, match="não disponíveis"):
        gerar_grafico_evolucao_coleta_lixo({}, tmp_path, "sem_dados")
