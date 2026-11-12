from decimal import Decimal
from pathlib import Path

import matplotlib.pyplot as plt
import pytest

from plotting.instrumentos_sudene_porte import (
    PORTES_EMPRESA,
    alturas_das_barras,
    desenhar_barras_por_porte,
    gerar_grafico_porte,
    percentuais_por_porte,
    texto_do_rotulo,
)
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


def test_portes_seguem_do_menor_para_o_maior_como_no_design():
    assert [rotulo for _, rotulo in PORTES_EMPRESA] == [
        "Mini", "Micro", "Pequeno", "Pequeno-\nMédio", "Médio I", "Médio II", "Grande",
    ]
    assert percentuais_por_porte(RECIFE, "contrato_") == [1.64, 72.54, 18.18, 4.15, 2.56, 0.58, 0.37]
    assert percentuais_por_porte(RECIFE, "valor_")[2] == 41.29


def test_barra_minima_para_porte_pequeno_e_zero_sem_barra():
    # Grande de Recife (0,37%) ainda aparece como um traço; Médio I de Igaci (0) não.
    assert alturas_das_barras([0.37, 0.0, 72.54]) == [0.6, 0.0, 72.54]


@pytest.mark.parametrize(
    ("percentual", "esperado"),
    [(72.54, "73%"), (0.37, "0%"), (0.0, "0%"), (100.0, "100%")],
)
def test_rotulo_tem_percentual_inteiro(percentual, esperado):
    assert texto_do_rotulo(percentual) == esperado


def test_coluna_ausente_vira_value_error_com_a_chave():
    linha = {**RECIFE, "valor_grande": None}

    with pytest.raises(ValueError, match="valor_grande"):
        percentuais_por_porte(linha, "valor_")


def test_todos_os_portes_zerados_vira_value_error():
    linha = {chave: Decimal(0) for chave in RECIFE}

    with pytest.raises(ValueError, match="zerados"):
        percentuais_por_porte(linha, "contrato_")


def _folgas_entre_rotulos_do_grupo(contratacoes: list[float], valores: list[float]) -> list[float]:
    fig = desenhar_barras_por_porte(contratacoes, valores)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    caixas = [texto.get_window_extent(renderer) for texto in fig.axes[0].texts]
    plt.close(fig)
    total = len(PORTES_EMPRESA)

    return [caixas[total + i].x0 - caixas[i].x1 for i in range(total)]


def test_rotulos_laranja_e_verde_do_mesmo_porte_nao_se_sobrepoem():
    # Pior caso: "100%" nas duas barras do grupo, na mesma altura.
    pior_caso = _folgas_entre_rotulos_do_grupo([100.0] * 7, [100.0] * 7)

    assert min(pior_caso) > 0


def test_titulo_do_card_repete_a_legenda_do_doc():
    fig = desenhar_barras_por_porte(
        percentuais_por_porte(RECIFE, "contrato_"), percentuais_por_porte(RECIFE, "valor_")
    )
    titulos = [texto.get_text() for texto in fig.texts]
    plt.close(fig)

    assert "Percentual de contratação e de valor investido por porte da empresa" in titulos


@pytest.mark.parametrize(("linha", "safe_city"), [(RECIFE, "recife_pe"), (IGACI, "igaci_al")])
def test_gera_o_png(tmp_path: Path, linha: dict, safe_city: str):
    nome = gerar_grafico_porte(linha, tmp_path, safe_city)

    assert nome == f"grafico_porte_{safe_city}.png"
    assert (tmp_path / nome).stat().st_size > 0


def test_tema_registra_um_grafico_so_pelo_marcador_do_doc():
    # O Doc passou de `*grafico_porte_contratacoes+grafico_porte_valor` (duas
    # pizzas) para `*grafico_porte` (barras) em 12/11/2026.
    nomes = [nome for nome, _, _ in GRAFICOS_POR_TEMA["instrumentos-sudene"]]

    assert "grafico_porte" in nomes
    assert "grafico_porte_contratacoes" not in nomes
    assert "grafico_porte_valor" not in nomes
    assert "instrumentos-sudene" not in GRAFICOS_AUTO_MARCADOR
