from decimal import Decimal
from pathlib import Path

import matplotlib.pyplot as plt
import pytest

from plotting.instrumentos_sudene_setor import (
    SERIES_SETOR,
    SETORES_ECONOMICOS,
    alturas_das_barras,
    desenhar_barras_por_setor,
    formatar_quantidade,
    formatar_valor_reais,
    gerar_grafico_setor,
    gerar_grafico_valor_total_tipo,
    marcas_do_eixo,
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
# Agricultura e infraestrutura zeradas (view de 13/11/2026).
RECIFE = _linha_da_view(
    ["0", "3", "4045", "129", "0", "23", "48", "93"],
    ["0", "154528.6", "359580433.74", "25884853.43", "0", "302000", "1804690.89", "18407853.45"],
)
# Igaci/AL: agroindústria, infraestrutura e turismo zerados; agricultura de 13/11/2026.
IGACI = _linha_da_view(
    ["31", "0", "401", "1", "0", "956", "2", "0"],
    ["4286320.12", "0", "3013505.85", "4729.41", "0", "15930324.2", "35899", "0"],
)


def test_setores_seguem_a_ordem_alfabetica_do_design():
    assert [setor for setor, _ in SETORES_ECONOMICOS] == [
        "agri", "agro", "comercio", "industria", "infra", "pecuaria", "pessoaf", "turismo",
    ]
    assert totais_por_setor(RECIFE, "{setor}_contrato") == [0.0, 3.0, 4045.0, 129.0, 0.0, 23.0, 48.0, 93.0]
    assert totais_por_setor(RECIFE, "valor_{setor}_contrato")[2] == 359580433.74


def test_setores_cobrem_os_8_da_origem_do_fne():
    # Regressão de 13/11/2026: sem agricultura e infraestrutura, a soma das
    # barras ficava abaixo de `contrato2025` em 2.003 municípios. Igaci/AL tem
    # 31 contratações de agricultura e 401 + 1 + 956 + 2 nos outros setores.
    assert sum(totais_por_setor(IGACI, "{setor}_contrato")) == 1391.0
    assert totais_por_setor(IGACI, "valor_{setor}_contrato")[0] == 4286320.12


def test_linha_sem_coluna_de_agricultura_vira_value_error():
    linha = dict(RECIFE)
    del linha["agri_contrato"]

    with pytest.raises(ValueError, match="agri_contrato"):
        totais_por_setor(linha, "{setor}_contrato")


def test_coluna_ausente_vira_value_error_com_a_chave():
    linha = dict(RECIFE)
    del linha["turismo_contrato"]

    with pytest.raises(ValueError, match="turismo_contrato"):
        totais_por_setor(linha, "{setor}_contrato")


@pytest.mark.parametrize("gerar", [gerar_grafico_setor, gerar_grafico_valor_total_tipo])
def test_serie_zerada_tira_so_o_proprio_card(tmp_path: Path, gerar):
    # Cada série tem o próprio card agora: zerada, ela some sozinha do
    # relatório (`_SO_VALOR`) e o card da outra série continua.
    zerado = _linha_da_view(["0"] * 8, ["0"] * 8)

    with pytest.raises(ValueError, match="zeradas"):
        gerar(zerado, tmp_path, "zerado")


def test_card_sai_mesmo_com_a_outra_serie_zerada(tmp_path: Path):
    so_valor = _linha_da_view(["0"] * 8, ["0", "0", "3013505.85", "4729.41", "0", "15930324.2", "35899", "0"])

    assert gerar_grafico_valor_total_tipo(so_valor, tmp_path, "so_valor").endswith(".png")


@pytest.mark.parametrize("tipo", ["quantidade", "valor"])
def test_rotulos_do_eixo_x_nao_se_sobrepoem(tipo):
    # Com 8 setores (13/11/2026) os grupos ficaram estreitos e "Agroindústria"
    # e "Infraestrutura" inteiros invadiam o rótulo vizinho.
    fig = desenhar_barras_por_setor(totais_por_setor(RECIFE, SERIES_SETOR[tipo].coluna), SERIES_SETOR[tipo])
    renderer = fig.canvas.get_renderer()
    caixas = [rotulo.get_window_extent(renderer) for rotulo in fig.axes[0].get_xticklabels()]
    plt.close(fig)

    assert all(esquerda.x1 < direita.x0 for esquerda, direita in zip(caixas, caixas[1:]))


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
        # Convenção dos cards: X,00 sai inteiro, como "4k" na quantidade.
        (302000, "R$ 302k"),
        (1804690.89, "R$ 1,80M"),
        (1500000, "R$ 1,50M"),
        (359580433.74, "R$ 359,58M"),
        (2.5e9, "R$ 2,50B"),
        # Fronteiras: arredondar para 1000 sobe uma faixa em vez de "R$ 1.000,00k".
        (999.5, "R$ 1k"),
        (999994.99, "R$ 999,99k"),
        (999995, "R$ 1M"),
        (999995000, "R$ 1B"),
    ],
)
def test_rotulo_do_valor(valor, esperado):
    assert formatar_valor_reais(valor) == esperado


@pytest.mark.parametrize(
    ("maior", "esperado"),
    [
        # Recife/PE no design: R$ 0, R$ 200M, R$ 400M.
        (359580433.74, [0.0, 2e8, 4e8]),
        (4045.0, [0.0, 2000.0, 4000.0, 6000.0]),
        (956.0, [0.0, 500.0, 1000.0]),
        (1.0, [0.0, 0.5, 1.0]),
    ],
)
def test_marcas_do_eixo_vao_de_zero_ate_passar_do_maior(maior, esperado):
    assert marcas_do_eixo(maior) == esperado


def test_barra_minima_para_valor_pequeno_e_zero_sem_barra():
    # Agroindústria de Recife (R$ 154,53k contra R$ 359,58M) ainda aparece como
    # um traço; turismo de Igaci (0) não ganha barra.
    recife = alturas_das_barras(totais_por_setor(RECIFE, "valor_{setor}_contrato"), 4e8)
    igaci = alturas_das_barras(totais_por_setor(IGACI, "valor_{setor}_contrato"), 2e7)

    assert recife[2] == 359580433.74
    assert recife[1] == 4e8 * 0.012
    assert igaci[1] == igaci[7] == 0.0


@pytest.mark.parametrize(
    ("gerar", "arquivo"),
    [
        (gerar_grafico_setor, "grafico_setor_quantidade_igaci_al.png"),
        (gerar_grafico_valor_total_tipo, "grafico_setor_valor_igaci_al.png"),
    ],
)
def test_gera_o_png_com_nome_novo(tmp_path: Path, gerar, arquivo):
    # Nome diferente do `grafico_setor_<cidade>.png` do card antigo de duas
    # séries, que `reusar_grafico` serviria até o próximo refresh das matviews.
    assert gerar(IGACI, tmp_path, "igaci_al") == arquivo
    assert (tmp_path / arquivo).stat().st_size > 0


@pytest.mark.parametrize(
    ("tipo", "coluna", "legenda"),
    [
        ("quantidade", "{setor}_contrato", "Quantidade de contratações por tipo de setor econômico"),
        ("valor", "valor_{setor}_contrato", "Valor investido por tipo de setor econômico"),
    ],
)
def test_titulo_do_card_repete_a_legenda_do_doc(tipo, coluna, legenda):
    # As legendas "Figura v" e "Figura w" do Doc saem logo abaixo dos cards; com
    # textos diferentes os dois pareciam descrever gráficos distintos.
    fig = desenhar_barras_por_setor(totais_por_setor(RECIFE, coluna), SERIES_SETOR[tipo])
    titulos = [texto.get_text() for texto in fig.texts]
    plt.close(fig)

    assert legenda in titulos


def test_tema_registra_os_dois_cards_pelos_marcadores_do_doc():
    nomes = [nome for nome, _, _ in GRAFICOS_POR_TEMA["instrumentos-sudene"]]

    # Presença, não posição: `nomes[-1]` quebraria no próximo gráfico do tema.
    assert "grafico_setor" in nomes
    assert "grafico_valor_total_tipo" in nomes
    assert "instrumentos-sudene" not in GRAFICOS_AUTO_MARCADOR
