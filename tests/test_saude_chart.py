from pathlib import Path

import pytest

from plotting.saude import (
    gerar_grafico_cobertura_vacinal,
    gerar_grafico_de_estabelecimento,
    gerar_grafico_publico_etario,
    gerar_grafico_taxa_mortalidade,
)


def _cidade_mortalidade_infantil():
    return {
        "mortalidade_infantil_serie": [
            {"ano": 2018, "taxa_mortalidade": 12.3},
            {"ano": 2019, "taxa_mortalidade": 10.1},
            {"ano": 2020, "taxa_mortalidade": 9.8},
        ]
    }


def test_gera_grafico_taxa_mortalidade(tmp_path: Path):
    arquivo = gerar_grafico_taxa_mortalidade(
        _cidade_mortalidade_infantil(), tmp_path, "campina_grande_pb"
    )

    assert arquivo == "grafico_taxa_mortalidade_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_taxa_mortalidade_exige_dados(tmp_path: Path):
    with pytest.raises(ValueError, match="Dados históricos de mortalidade infantil"):
        gerar_grafico_taxa_mortalidade({}, tmp_path, "sem_dados")


def _cidade_estabelecimentos_saude():
    return {
        "estabelecimentos_saude_serie": [
            {"ano": 2018, "total_estabelecimentos": 850},
            {"ano": 2019, "total_estabelecimentos": 920},
            {"ano": 2020, "total_estabelecimentos": 1010},
        ]
    }


def test_gera_grafico_de_estabelecimento(tmp_path: Path):
    arquivo = gerar_grafico_de_estabelecimento(
        _cidade_estabelecimentos_saude(), tmp_path, "campina_grande_pb"
    )

    assert arquivo == "grafico_de_estabelecimento_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_de_estabelecimento_exige_dados(tmp_path: Path):
    with pytest.raises(
        ValueError, match="Dados históricos de estabelecimentos de saúde"
    ):
        gerar_grafico_de_estabelecimento({}, tmp_path, "sem_dados")


def _cidade_cobertura_vacinal():
    return {
        "cobertura_vacinal_serie": [
            {"vacina": "BCG", "cobertura_vacinal": 98.5},
            {"vacina": "Poliomielite", "cobertura_vacinal": 87.2},
            {"vacina": "Hepatite B", "cobertura_vacinal": 91.0},
        ]
    }


def test_gera_grafico_cobertura_vacinal(tmp_path: Path):
    arquivo = gerar_grafico_cobertura_vacinal(
        _cidade_cobertura_vacinal(), tmp_path, "campina_grande_pb"
    )

    assert arquivo == "grafico_cobertura_vacinal_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_gera_grafico_cobertura_vacinal_com_muitas_vacinas(tmp_path: Path):
    # A altura da figura varia com a quantidade de vacinas; garante que o
    # card também é gerado corretamente com uma lista bem maior.
    cidade = {
        "cobertura_vacinal_serie": [
            {"vacina": f"Vacina {indice}", "cobertura_vacinal": 60 + indice}
            for indice in range(14)
        ]
    }

    arquivo = gerar_grafico_cobertura_vacinal(cidade, tmp_path, "campina_grande_pb")

    assert arquivo == "grafico_cobertura_vacinal_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_cobertura_vacinal_exige_dados(tmp_path: Path):
    with pytest.raises(ValueError, match="Dados de cobertura vacinal"):
        gerar_grafico_cobertura_vacinal({}, tmp_path, "sem_dados")


def _cidade_publico_etario():
    return {
        "publico_etario_ao_nascer": 1200,
        "publico_etario_menor_1_ano": 3400,
        "publico_etario_1_ano": 3100,
        "publico_etario_multifaixa": 8900,
        "dose_etario_ao_nascer": 1100,
        "dose_etario_menor_1_ano": 3000,
        "dose_etario_1_ano": 2800,
        "dose_etario_multifaixa": 7600,
    }


def test_gera_grafico_publico_etario(tmp_path: Path):
    arquivo = gerar_grafico_publico_etario(
        _cidade_publico_etario(), tmp_path, "campina_grande_pb"
    )

    assert arquivo == "grafico_publico_etario_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_publico_etario_sem_dados_estoura_key_error(tmp_path: Path):
    # Diferente das demais funções deste módulo, `gerar_grafico_publico_etario`
    # acessa os campos de `cidade` direto (sem `.get()`), então hoje ela não
    # degrada para um `ValueError` amigável quando os dados faltam — estoura
    # `KeyError`. Este teste documenta o comportamento atual, não o ideal.
    with pytest.raises(KeyError):
        gerar_grafico_publico_etario({}, tmp_path, "sem_dados")
