from decimal import Decimal
from pathlib import Path

import pytest

from plotting.instrumentos_sudene import (
    gerar_grafico_quantidade_de_contratacoes,
    gerar_grafico_valor_investido,
    quantidade_de_contratacoes_por_ano,
    valor_contratado_em_reais,
    valor_contratado_por_ano,
)
from services.generation import GRAFICOS_AUTO_MARCADOR, GRAFICOS_POR_TEMA


def _linha_da_view(contratos, valores, unidades) -> dict:
    # Mesmo formato de `relatorios_auto.instrsudene_munic`: uma coluna por ano.
    linha = {}
    for ano, contrato, valor, unidade in zip(range(2021, 2026), contratos, valores, unidades):
        linha[f"contrato{ano}"] = Decimal(contrato)
        linha[f"valor_contrato{ano}"] = Decimal(valor)
        linha[f"valor_contrato{ano}unid"] = unidade
    return linha


# Recife/PE na view do Gamma em 04/11/2026: os números do exemplo do design.
RECIFE = _linha_da_view(
    (1015, 1317, 2223, 4274, 4341),
    ("785.66", "403.30", "315.87", "325.95", "406.13"),
    ("milhões",) * 5,
)
# Alcântara/MA: a unidade muda no meio da série e aparece no singular.
ALCANTARA = _linha_da_view(
    (10, 12, 20, 30, 35),
    ("499.00", "426.00", "1.40", "2.13", "2.48"),
    ("mil", "mil", "milhão", "milhões", "milhões"),
)


def test_quantidade_de_contratacoes_segue_os_anos_da_view():
    assert quantidade_de_contratacoes_por_ano(RECIFE) == [1015, 1317, 2223, 4274, 4341]


def test_valor_volta_para_reais_mesmo_com_unidade_trocando_no_meio_da_serie():
    assert valor_contratado_por_ano(ALCANTARA) == pytest.approx(
        [499_000, 426_000, 1_400_000, 2_130_000, 2_480_000]
    )


@pytest.mark.parametrize(
    ("unidade", "esperado"),
    [("reais", 0.0), ("bilhão", 1.2e9), ("Milhões ", 1.2e6), (None, 1.2)],
)
def test_valor_em_reais_aceita_as_unidades_da_view(unidade, esperado):
    valor = "0" if unidade == "reais" else "1.2"

    assert valor_contratado_em_reais(Decimal(valor), unidade) == pytest.approx(esperado)


def test_unidade_desconhecida_vira_erro_com_o_valor_recebido():
    with pytest.raises(ValueError, match="'trilhões'"):
        valor_contratado_em_reais(Decimal(1), "trilhões")


def test_ano_ausente_vira_value_error_para_o_grafico_sair_do_relatorio():
    # `gerar_graficos_do_tema` só tolera ValueError (_SO_VALOR) neste tema.
    linha = {**RECIFE, "contrato2023": None}

    with pytest.raises(ValueError, match="2023"):
        quantidade_de_contratacoes_por_ano(linha)


@pytest.mark.parametrize(
    ("gerar", "arquivo"),
    [
        (gerar_grafico_quantidade_de_contratacoes, "grafico_quantidade_de_contratacoes_recife_pe.png"),
        (gerar_grafico_valor_investido, "grafico_valor_investido_recife_pe.png"),
    ],
)
def test_gera_os_cards_de_recife(tmp_path: Path, gerar, arquivo):
    assert gerar(RECIFE, tmp_path, "recife_pe") == arquivo
    assert (tmp_path / arquivo).is_file()


def test_gera_card_de_valor_para_municipio_sem_contratacao_em_2021(tmp_path: Path):
    # 81 municípios da view têm 0 contratações e "0.00 reais" em 2021.
    linha = _linha_da_view(
        (0, 3, 5, 8, 10), ("0.00", "1.17", "2.00", "3.10", "11.75"),
        ("reais", "milhão", "milhões", "milhões", "milhões"),
    )

    assert gerar_grafico_valor_investido(linha, tmp_path, "acucena_mg").endswith(".png")


def test_tema_registra_os_dois_graficos_pelos_marcadores_do_doc():
    nomes = [nome for nome, _, _ in GRAFICOS_POR_TEMA["instrumentos-sudene"]]

    assert nomes[:2] == ["grafico_quantidade_de_contratacoes", "grafico_valor_investido"]
    assert "instrumentos-sudene" not in GRAFICOS_AUTO_MARCADOR


def test_eixo_de_valor_nao_repete_rotulo_e_usa_singular_abaixo_de_dois():
    # Alcântara: marcas de 0,5 em 0,5 milhão saíam "R$ 1 milhões" duas vezes.
    from plotting.instrumentos_sudene import _formatadores_de_reais

    eixo, ponto = _formatadores_de_reais(2_480_000)

    assert [eixo(v) for v in (0, 500_000, 1_000_000, 1_500_000, 2_000_000)] == [
        "R$ 0", "R$ 0,5 milhão", "R$ 1 milhão", "R$ 1,5 milhão", "R$ 2 milhões",
    ]
    assert ponto(2_480_000) == "2,5 Mi"


@pytest.mark.parametrize(
    ("valores", "esperado"),
    [
        # Igaci/AL: 2021 sobe forte para 2022 (o rótulo centrado cortava a linha);
        # 2024 é um vale raso entre 21,41 e 23,27.
        ([9.83, 20.21, 21.41, 21.28, 23.27], ["acima_esquerda", "acima_esquerda", "acima", "abaixo", "acima"]),
        # Recife/PE: pico em 2021, vale em 2023.
        ([785.66, 403.30, 315.87, 325.95, 406.13], ["acima", "acima_direita", "abaixo", "acima_esquerda", "acima"]),
    ],
)
def test_rotulo_fica_do_lado_por_onde_a_linha_nao_passa(valores, esperado):
    from plotting.instrumentos_sudene import posicao_do_rotulo

    assert [posicao_do_rotulo(valores, i) for i in range(len(valores))] == esperado
