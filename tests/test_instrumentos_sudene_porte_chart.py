from decimal import Decimal
from pathlib import Path

import pytest

from plotting.instrumentos_sudene_porte import (
    PORTES_EMPRESA,
    gerar_grafico_porte_contratacoes,
    gerar_grafico_porte_valor,
    percentuais_por_porte,
)
from plotting.saneamento import _posicoes_dos_rotulos
from services.generation import GRAFICOS_AUTO_MARCADOR, GRAFICOS_POR_TEMA


def _linha_da_view(contratos: dict[str, str], valores: dict[str, str]) -> dict:
    # Mesmo formato de `relatorios_auto.instrsudene_munic`: contrato_<porte> e
    # valor_<porte>, já em percentual.
    linha = {f"contrato_{porte}": Decimal(pct) for porte, pct in contratos.items()}
    linha.update({f"valor_{porte}": Decimal(pct) for porte, pct in valores.items()})
    return linha


# Recife/PE na view do Gamma em 04/11/2026: os números do exemplo do design.
RECIFE = _linha_da_view(
    {"mini": "1.64", "micro": "72.54", "pequeno": "18.18", "peq_medio": "4.15",
     "media1": "2.56", "media2": "0.58", "grande": "0.37"},
    {"mini": "0.52", "micro": "6.82", "pequeno": "41.29", "peq_medio": "33.13",
     "media1": "10.72", "media2": "3.64", "grande": "3.87"},
)
# Igaci/AL: três portes com 0% nos dois gráficos.
IGACI = _linha_da_view(
    {"mini": "69.88", "micro": "28.40", "pequeno": "1.15", "peq_medio": "0.58",
     "media1": "0", "media2": "0", "grande": "0"},
    {"mini": "68.97", "micro": "10.61", "pequeno": "10.63", "peq_medio": "9.79",
     "media1": "0", "media2": "0", "grande": "0"},
)


def test_percentuais_seguem_a_ordem_crescente_de_porte():
    assert PORTES_EMPRESA[0][1] == "Mini"
    assert percentuais_por_porte(RECIFE, "contrato_") == [1.64, 72.54, 18.18, 4.15, 2.56, 0.58, 0.37]
    assert percentuais_por_porte(RECIFE, "valor_")[2] == 41.29


def test_porte_com_zero_nao_ganha_rotulo():
    # `_posicoes_dos_rotulos` só posiciona fatia > 0: Médio I, Médio II e
    # Grande (índices 4, 5 e 6) ficam fora do desenho em Igaci.
    rotulados = _posicoes_dos_rotulos(percentuais_por_porte(IGACI, "contrato_"))

    assert sorted(rotulados) == [0, 1, 2, 3]


def test_coluna_ausente_vira_value_error_com_a_chave():
    linha = {**RECIFE, "valor_grande": None}

    with pytest.raises(ValueError, match="valor_grande"):
        percentuais_por_porte(linha, "valor_")


def test_todos_os_portes_zerados_vira_value_error():
    linha = {chave: Decimal(0) for chave in RECIFE}

    with pytest.raises(ValueError, match="zerados"):
        percentuais_por_porte(linha, "contrato_")


@pytest.mark.parametrize(
    ("gerar", "arquivo"),
    [
        (gerar_grafico_porte_contratacoes, "grafico_porte_contratacoes_recife_pe.png"),
        (gerar_grafico_porte_valor, "grafico_porte_valor_recife_pe.png"),
    ],
)
def test_gera_as_pizzas_de_recife(tmp_path: Path, gerar, arquivo):
    assert gerar(RECIFE, tmp_path, "recife_pe") == arquivo
    assert (tmp_path / arquivo).is_file()


def test_gera_pizza_com_portes_zerados(tmp_path: Path):
    assert gerar_grafico_porte_valor(IGACI, tmp_path, "igaci_al").endswith(".png")


def test_tema_registra_as_pizzas_pelos_marcadores_do_doc():
    nomes = [nome for nome, _, _ in GRAFICOS_POR_TEMA["instrumentos-sudene"]]

    assert nomes[-2:] == ["grafico_porte_contratacoes", "grafico_porte_valor"]
    assert "instrumentos-sudene" not in GRAFICOS_AUTO_MARCADOR
