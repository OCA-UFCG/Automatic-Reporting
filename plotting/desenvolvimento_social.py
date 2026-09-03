import pathlib
from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from plotting.demografia import _salvar_figura_com_fundo_branco
from utils.formatting import coerce_para_float

_CATEGORIAS_IDHM = (
    ("Muito Baixo", "#D64550"),
    ("Baixo", "#F4A11A"),
    ("Médio", "#FFC845"),
    ("Alto", "#3FA34D"),
    ("Muito Alto", "#5FA8D3"),
)

_coerce_numero = partial(coerce_para_float, default=None)


def _classificar_idhm(valor: float) -> str:
    if valor < 0.5:
        return "Muito Baixo"
    if valor < 0.6:
        return "Baixo"
    if valor < 0.7:
        return "Médio"
    if valor < 0.8:
        return "Alto"
    return "Muito Alto"


def gerar_grafico_de_desenvolvimento_social(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    pontos = [
        (ano, _coerce_numero(cidade.get(campo)))
        for ano, campo in (
            ("1991", "idhm_1991"),
            ("2000", "idhm_2000"),
            ("2010", "idhm_2010"),
        )
    ]
    pontos = [(ano, valor) for ano, valor in pontos if valor is not None]
    if not pontos:
        raise ValueError("Dados históricos de IDHM não disponíveis.")

    anos = [ano for ano, _ in pontos]
    valores = [valor for _, valor in pontos]

    cores_por_categoria = dict(_CATEGORIAS_IDHM)
    cores = [cores_por_categoria[_classificar_idhm(valor)] for valor in valores]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_de_desenvolvimento_social_{safe_city}.png"

    x = np.arange(len(anos))

    fig, ax = plt.subplots(figsize=(8, 3.6))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    barras = ax.bar(x, valores, width=0.5, color=cores, zorder=3)

    limite = max(valores) * 1.22 if valores else 1
    ax.set_ylim(0, limite)

    for barra, valor in zip(barras, valores):
        ax.text(
            barra.get_x() + barra.get_width() / 2,
            valor + limite * 0.025,
            f"{valor:.2f}".replace(".", ","),
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight=600,
            color="#4A4A4A",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(anos, fontsize=9)
    ax.set_yticks([])

    ax.grid(
        axis="y",
        linestyle="--",
        linewidth=0.5,
        color="#D9D9D9",
        alpha=0.6,
        zorder=0,
    )
    ax.set_axisbelow(True)

    ax.tick_params(axis="both", length=0, labelsize=9, colors="#4A4A4A")
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color("#4A4A4A")

    handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=cor,
            markeredgecolor="none",
            markersize=8,
            label=nome,
        )
        for nome, cor in _CATEGORIAS_IDHM
    ]
    ax.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.14),
        ncol=5,
        frameon=False,
        fontsize=8,
    )

    _salvar_figura_com_fundo_branco(fig, ax, chart_file)

    return chart_file.name
