from decimal import Decimal
from pathlib import Path

import pytest

from plotting.saneamento import (
    _ANOS_DINAMICA_ESGOTO,
    _pontos_por_ano,
    gerar_grafico_coleta_lixo,
    gerar_grafico_dinamica_esgoto,
    gerar_grafico_esgotamento_sanitario,
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


def test_gera_dinamica_esgoto(tmp_path: Path):
    # Campina Grande/PB: 2000 vem como string (fonte antiga da view), 2010 e
    # 2022 como Decimal — mistura real que o parser precisa suportar.
    cidade = {
        "esgoto_rede_2000": "68.4",
        "esgoto_rede_2010": Decimal("79.4"),
        "esgoto_rede_2022": Decimal("86.6"),
    }

    arquivo = gerar_grafico_dinamica_esgoto(cidade, tmp_path, "campina_grande_pb")

    assert arquivo == "grafico_dinamica_esgoto_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_dinamica_esgoto_mantem_ano_com_zero(tmp_path: Path):
    # 0% é cobertura real, não falta de dado: 469 dos 2.074 municípios da view
    # têm 0% em 2000. O ano precisa virar barra zerada, não sumir do gráfico.
    cidade = {
        "esgoto_rede_2000": "0",
        "esgoto_rede_2010": Decimal("12.5"),
        "esgoto_rede_2022": Decimal("30.0"),
    }

    assert _pontos_por_ano(cidade, _ANOS_DINAMICA_ESGOTO) == [
        ("2000", 0.0),
        ("2010", 12.5),
        ("2022", 30.0),
    ]
    arquivo = gerar_grafico_dinamica_esgoto(cidade, tmp_path, "com_zero")
    assert (tmp_path / arquivo).is_file()


def test_dinamica_esgoto_omite_ano_sem_dado(tmp_path: Path):
    # "sem dados" é o texto que a view guarda em alguns municípios; junto com
    # None, é o único caso que deve sair do gráfico.
    cidade = {
        "esgoto_rede_2000": "sem dados",
        "esgoto_rede_2010": None,
        "esgoto_rede_2022": Decimal("30.0"),
    }

    assert _pontos_por_ano(cidade, _ANOS_DINAMICA_ESGOTO) == [("2022", 30.0)]


def test_grafico_dinamica_esgoto_exige_dados(tmp_path: Path):
    cidade = {
        "esgoto_rede_2000": None,
        "esgoto_rede_2010": "sem dados",
        "esgoto_rede_2022": None,
    }
    with pytest.raises(ValueError, match="não disponíveis"):
        gerar_grafico_dinamica_esgoto(cidade, tmp_path, "sem_dados")


def test_gera_coleta_lixo(tmp_path: Path):
    # Campina Grande/PB.
    cidade = {
        "coleta_2010": Decimal("94.8"),
        "coleta_2022": Decimal("97.5"),
    }

    arquivo = gerar_grafico_coleta_lixo(cidade, tmp_path, "campina_grande_pb")

    assert arquivo == "grafico_coleta_lixo_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_coleta_lixo_exige_dados(tmp_path: Path):
    cidade = {
        "coleta_2010": None,
        "coleta_2022": "sem dados",
    }
    with pytest.raises(ValueError, match="não disponíveis"):
        gerar_grafico_coleta_lixo(cidade, tmp_path, "sem_dados")
