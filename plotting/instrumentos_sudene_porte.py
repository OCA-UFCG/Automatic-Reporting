"""Gráfico de porte da empresa do macrotema Instrumentos da Sudene (FNE, 2025).

Um card de barras agrupadas, que o Doc insere com o marcador `*grafico_porte`
acima da legenda "Percentual de contratação e de valor investido por porte da
empresa". Em cada porte há duas barras: laranja para a fatia das contratações e
verde para a fatia do valor investido.

LEGACY: até 12/11/2026 eram duas pizzas lado a lado
(`*grafico_porte_contratacoes+grafico_porte_valor`, PR #246). O design trocou
para um gráfico só, e o Doc passou a usar o marcador `*grafico_porte`.

A view `relatorios_auto.instrsudene_munic` já entrega o percentual de cada porte
(`contrato_<porte>` e `valor_<porte>`, somando ~100). Recife/PE em 2025:
micro 72,54% das contratações, pequeno 41,29% do valor.
"""

import pathlib

from matplotlib.ticker import FuncFormatter

from plotting import (
    ESCALA_FONTE,
    FONTE_ROTULO_VALOR,
    FONTE_TICK,
    iniciar_card_grafico,
    reusar_grafico,
    salvar_card_grafico,
)
from plotting.economia_renda import _reservar_espaco_rotulo_x
from utils.formatting import formatar_numero_ptbr

# (sufixo da coluna na view, rótulo no eixo X). INTENTIONAL: do menor porte para
# o maior, como no design das barras; as pizzas antigas usavam ordem alfabética.
# "Pequeno-Médio" quebra no hífen: numa linha só encostava no "Pequeno" ao lado.
PORTES_EMPRESA = (
    ("mini", "Mini"),
    ("micro", "Micro"),
    ("pequeno", "Pequeno"),
    ("peq_medio", "Pequeno-\nMédio"),
    ("media1", "Médio I"),
    ("media2", "Médio II"),
    ("grande", "Grande"),
)
# IMPORTANT: igual à legenda "Figura z" do Doc, que sai logo abaixo do card, como
# no gráfico de setor (`TITULO_CARD_SETOR`). O design abrevia para "Contratação e
# de valor investido…"; com textos diferentes os dois pareciam descrever gráficos
# distintos. Se o Doc mudar a legenda, mude aqui também.
TITULO_CARD_PORTE = "Percentual de contratação e de valor investido por porte da empresa"
# Cores medidas do design, as mesmas do gráfico de setor
# (`plotting/instrumentos_sudene_setor.py`): laranja = contratações, verde = valor.
_COR_CONTRATACOES = "#DD7402"
_COR_VALOR = "#018F39"
_COR_TEXTO = "#514C50"
_LARGURA_BARRA = 0.36
# Distância do centro do grupo até o centro de cada barra. WARNING: com 0,19 os
# rótulos "100%" das duas barras do mesmo porte (município com um porte só) se
# sobrepunham. O teste de folga mede isso.
_DESLOCAMENTO_BARRA = 0.21
# Altura mínima, em pontos percentuais, de um porte com valor > 0: no design o
# Grande de Recife (0,37% das contratações) ainda aparece como um traço. Zero
# continua sem barra.
_ALTURA_MINIMA = 0.6
# O eixo vai sempre a 100%, como no design, e a folga acima cabe o rótulo de
# uma barra de 100% (município com um porte só).
_TOPO_EIXO = 100
_FOLGA_TOPO = 8


def percentuais_por_porte(cidade: dict, prefixo: str) -> list[float]:
    """Percentual de cada porte em `PORTES_EMPRESA`, lido de `<prefixo><porte>`.

    Ex.: percentuais_por_porte(recife, "contrato_")[1] -> 72.54 (micro).
    """
    chaves = [f"{prefixo}{porte}" for porte, _ in PORTES_EMPRESA]
    faltando = [chave for chave in chaves if cidade.get(chave) is None]
    if faltando:
        raise ValueError(f"Percentuais por porte ausentes: {faltando}; esperado número em cada coluna.")

    percentuais = [float(cidade[chave]) for chave in chaves]
    if sum(percentuais) <= 0:
        raise ValueError(f"Percentuais por porte zerados em '{prefixo}*': {percentuais}.")

    return percentuais


def alturas_das_barras(percentuais: list[float]) -> list[float]:
    """Altura de cada barra: o próprio percentual, com piso de `_ALTURA_MINIMA`
    para porte > 0. Ex.: [0.37, 0, 72.54] -> [0.6, 0.0, 72.54]."""
    return [max(pct, _ALTURA_MINIMA) if pct > 0 else 0.0 for pct in percentuais]


def texto_do_rotulo(percentual: float) -> str:
    """Percentual inteiro, como no design: 72,54 -> "73%". O texto do Doc é que
    traz as duas casas. Zero também ganha rótulo: sem barra, o "0%" é o que diz
    que o porte não teve contratação."""
    return f"{formatar_numero_ptbr(percentual)}%"


def _desenhar_serie(ax, posicoes: list[float], percentuais: list[float], cor: str) -> None:
    alturas = alturas_das_barras(percentuais)
    ax.bar(posicoes, alturas, width=_LARGURA_BARRA, color=cor, zorder=3)
    for posicao, altura, pct in zip(posicoes, alturas, percentuais):
        ax.annotate(
            texto_do_rotulo(pct), (posicao, altura), xytext=(0, 4), textcoords="offset points",
            ha="center", va="bottom", fontsize=FONTE_ROTULO_VALOR * 0.85 * ESCALA_FONTE,
            color=_COR_TEXTO, zorder=4,
        )


def _estilizar_eixos(ax) -> None:
    ax.set_xticks(range(len(PORTES_EMPRESA)))
    ax.set_xticklabels([rotulo for _, rotulo in PORTES_EMPRESA])
    ax.set_xlim(-0.6, len(PORTES_EMPRESA) - 0.4)
    ax.set_ylim(0, _TOPO_EIXO + _FOLGA_TOPO)
    # Marcas de 10 em 10 até 100%, como no design; a folga acima de 100 não ganha marca.
    ax.set_yticks(range(0, _TOPO_EIXO + 1, 10))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda valor, _: f"{valor:.0f}%"))
    ax.tick_params(axis="both", length=0, colors=_COR_TEXTO, labelsize=FONTE_TICK * ESCALA_FONTE)
    ax.tick_params(axis="x", pad=8)
    for lado in ("left", "right", "top"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(_COR_TEXTO)


def desenhar_barras_por_porte(contratacoes: list[float], valores: list[float]):
    """Monta o card (sem salvar) e devolve a figura, para o teste medir os rótulos."""
    fig, ax = iniciar_card_grafico((8, 4.4), TITULO_CARD_PORTE, margem_esquerda=0.09)
    _reservar_espaco_rotulo_x(fig, ax, reserva_polegadas=0.3)
    centros = range(len(PORTES_EMPRESA))
    _desenhar_serie(ax, [c - _DESLOCAMENTO_BARRA for c in centros], contratacoes, _COR_CONTRATACOES)
    _desenhar_serie(ax, [c + _DESLOCAMENTO_BARRA for c in centros], valores, _COR_VALOR)
    _estilizar_eixos(ax)

    return fig


def gerar_grafico_porte(cidade: dict, OUTPUT_DIR: pathlib.Path, safe_city: str) -> str:
    contratacoes = percentuais_por_porte(cidade, "contrato_")
    valores = percentuais_por_porte(cidade, "valor_")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_porte_{safe_city}.png"
    reuso = reusar_grafico(chart_file)
    if reuso is not None:
        return reuso

    salvar_card_grafico(desenhar_barras_por_porte(contratacoes, valores), chart_file)

    return chart_file.name
