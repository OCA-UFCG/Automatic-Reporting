from decimal import Decimal
from pathlib import Path

import pytest

from plotting.instrumentos_sudene_setor import (
    SETORES_ECONOMICOS,
    alturas_normalizadas,
    desenhar_barras_por_setor,
    formatar_quantidade,
    formatar_valor_reais,
    gerar_grafico_setor,
    totais_por_setor,
)
from services.generation import GRAFICOS_AUTO_MARCADOR, GRAFICOS_POR_TEMA


def _linha_da_view(contratos: list[str], valores: list[str]) -> dict:
    # Mesmo formato de `relatorios_auto.instrsudene_munic`: <setor>_contrato e
    # valor_<setor>_contrato, números absolutos com o valor em reais.
    linha = {}
    for (setor, _), contrato, valor in zip(SETORES_ECONOMICOS, contratos, valores):
        linha[f"{setor}_contrato"] = Decimal(contrato)
        linha[f"valor_{setor}_contrato"] = Decimal(valor)
    return linha


# Recife/PE na view do Gamma em 06/11/2026: os números do exemplo do design.
RECIFE = _linha_da_view(
    ["3", "4045", "129", "23", "48", "93"],
    ["154528.6", "359580433.74", "25884853.43", "302000", "1804690.89", "18407853.45"],
)
# Igaci/AL: agroindústria e turismo zerados.
IGACI = _linha_da_view(
    ["0", "401", "1", "956", "2", "0"],
    ["0", "3013505.85", "4729.41", "15930324.2", "35899", "0"],
)


def test_setores_seguem_a_ordem_alfabetica_do_design():
    assert [setor for setor, _ in SETORES_ECONOMICOS] == [
        "agro", "comercio", "industria", "pecuaria", "pessoaf", "turismo",
    ]
    assert totais_por_setor(RECIFE, "{setor}_contrato") == [3.0, 4045.0, 129.0, 23.0, 48.0, 93.0]
    assert totais_por_setor(RECIFE, "valor_{setor}_contrato")[1] == 359580433.74


def test_coluna_ausente_vira_value_error_com_a_chave():
    linha = dict(RECIFE)
    del linha["turismo_contrato"]

    with pytest.raises(ValueError, match="turismo_contrato"):
        totais_por_setor(linha, "{setor}_contrato")


def test_as_duas_series_zeradas_vira_value_error(tmp_path: Path):
    zerado = _linha_da_view(["0"] * 6, ["0"] * 6)

    with pytest.raises(ValueError, match="zerados"):
        gerar_grafico_setor(zerado, tmp_path, "zerado")


@pytest.mark.parametrize(
    ("contratos", "valores"),
    [
        (["0", "401", "1", "956", "2", "0"], ["0"] * 6),
        (["0"] * 6, ["0", "3013505.85", "4729.41", "15930324.2", "35899", "0"]),
    ],
    ids=["so_contratacoes", "so_valores"],
)
def test_uma_serie_zerada_ainda_gera_o_card(tmp_path: Path, contratos, valores):
    nome = gerar_grafico_setor(_linha_da_view(contratos, valores), tmp_path, "uma_serie")

    assert (tmp_path / nome).stat().st_size > 0


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (0, "0"), (3, "3"), (999, "999"), (4045, "4k"), (1530, "1,5k"), (12345, "12,3k"),
        # Fronteira k -> M: o sufixo sai do valor arredondado, não do bruto.
        (999949, "999,9k"), (999950, "1M"), (999999, "1M"), (1250000, "1,3M"),
    ],
)
def test_rotulo_da_quantidade(valor, esperado):
    assert formatar_quantidade(valor) == esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (0, "R$ 0"),
        (950, "R$ 950"),
        (154528.6, "R$ 154,53k"),
        (302000, "R$ 302,00k"),
        (1804690.89, "R$ 1,80M"),
        (359580433.74, "R$ 359,58M"),
        (2.5e9, "R$ 2,50B"),
        # Fronteiras: arredondar para 1000 sobe uma faixa em vez de "R$ 1.000,00k".
        (999.5, "R$ 1,00k"),
        (999994.99, "R$ 999,99k"),
        (999995, "R$ 1,00M"),
        (999995000, "R$ 1,00B"),
    ],
)
def test_rotulo_do_valor(valor, esperado):
    assert formatar_valor_reais(valor) == esperado


def test_barra_minima_para_valor_pequeno_e_zero_sem_barra():
    # Agroindústria de Recife (3 contra 4.045) ainda aparece como um traço;
    # turismo de Igaci (0) não ganha barra.
    recife = alturas_normalizadas(totais_por_setor(RECIFE, "{setor}_contrato"))
    igaci = alturas_normalizadas(totais_por_setor(IGACI, "{setor}_contrato"))

    assert recife[1] == 1.0
    assert 0 < recife[0] < 0.02
    assert igaci[0] == igaci[5] == 0.0


def _folgas_entre_rotulos_do_grupo(quantidades: list[float], valores: list[float]) -> list[float]:
    fig = desenhar_barras_por_setor(quantidades, valores)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    caixas = [texto.get_window_extent(renderer) for texto in fig.axes[0].texts]
    total = len(SETORES_ECONOMICOS)

    return [caixas[total + i].x0 - caixas[i].x1 for i in range(total)]


def test_rotulos_laranja_e_verde_do_mesmo_setor_nao_se_sobrepoem():
    # Regressão: com as barras mais juntas, "4k" e "R$ 359,58M" de Recife
    # encostavam, e o pior caso ("999" e "R$ 999,99M") se sobrepunha.
    recife = _folgas_entre_rotulos_do_grupo(
        totais_por_setor(RECIFE, "{setor}_contrato"), totais_por_setor(RECIFE, "valor_{setor}_contrato")
    )
    pior_caso = _folgas_entre_rotulos_do_grupo([999.0] * 6, [999.99e6] * 6)

    assert min(recife) > 5
    assert min(pior_caso) > 0


def test_gera_o_png(tmp_path: Path):
    nome = gerar_grafico_setor(IGACI, tmp_path, "igaci_al")

    assert nome == "grafico_setor_igaci_al.png"
    assert (tmp_path / nome).stat().st_size > 0


def test_tema_registra_o_grafico_pelo_marcador_do_doc():
    nomes = [nome for nome, _, _ in GRAFICOS_POR_TEMA["instrumentos-sudene"]]

    assert nomes[-1] == "grafico_setor"
    assert "instrumentos-sudene" not in GRAFICOS_AUTO_MARCADOR
