from pathlib import Path

import pytest

from plotting import ESCALA_FONTE, iniciar_card_grafico
from plotting.saude import (
    _deslocamento_minimo_para_rotulos,
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


def test_gera_grafico_publico_etario_com_valores_grandes(tmp_path: Path):
    # Municípios maiores podem ter público-alvo/doses de 5-6 dígitos em
    # "multifaixa etária" — a folga original entre as duas barras da mesma
    # categoria era fixa e não escalava com a largura do texto do rótulo.
    cidade = {
        "publico_etario_ao_nascer": 123456,
        "publico_etario_menor_1_ano": 123450,
        "publico_etario_1_ano": 99999,
        "publico_etario_multifaixa": 100001,
        "dose_etario_ao_nascer": 123400,
        "dose_etario_menor_1_ano": 123449,
        "dose_etario_1_ano": 99998,
        "dose_etario_multifaixa": 100000,
    }

    arquivo = gerar_grafico_publico_etario(cidade, tmp_path, "cidade_grande")

    assert arquivo == "grafico_publico_etario_cidade_grande.png"
    assert (tmp_path / arquivo).is_file()


def test_deslocamento_minimo_para_rotulos_cresce_com_texto_largo(tmp_path: Path):
    # Regressão: rótulos largos ("123.456") colidiam porque a folga entre as
    # duas barras de cada categoria era um valor fixo, pensado só pros
    # valores de teste (4 dígitos). O deslocamento mínimo precisa crescer
    # junto com a largura real do texto renderizado.
    largura = 0.24
    espaco = 0.06
    fontsize = 11 * ESCALA_FONTE
    deslocamento_base = largura / 2 + espaco / 2

    # Mesma geometria de `gerar_grafico_publico_etario` (4 categorias, barras
    # nos dois lados de cada uma): o xlim autoescalado depende de quantas
    # categorias existem, então precisa refletir o uso real da função.
    fig, ax = iniciar_card_grafico((10, 4.6), "titulo")
    x = [0, 1, 2, 3]
    ax.bar([xi - deslocamento_base for xi in x], [10] * 4, width=largura)
    ax.bar([xi + deslocamento_base for xi in x], [10] * 4, width=largura)
    fig.canvas.draw()
    ax.set_xlim(*ax.get_xlim())

    deslocamento_curto = _deslocamento_minimo_para_rotulos(
        fig, ax, ["1.200", "1.100"], largura, espaco, fontsize
    )
    deslocamento_longo = _deslocamento_minimo_para_rotulos(
        fig, ax, ["123.456", "123.400"], largura, espaco, fontsize
    )

    assert deslocamento_curto == pytest.approx(deslocamento_base)
    assert deslocamento_longo > deslocamento_curto
