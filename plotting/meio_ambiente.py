import pathlib

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter

from plotting import ESCALA_FONTE

# (campo no contexto, rótulo da legenda, cor) — ordem e cores espelham o Doc.
# Campos vêm de relatorios_auto.ambiente (percentual da área municipal em
# cada classe de aridez, ano de 2021).
_CATEGORIAS_ARIDEZ = (
    ("area_arida2021_per", "Árido", "#C0392B"),
    ("area_semiarida2021_per", "Semiárido", "#E67E22"),
    ("area_subumida2021_per", "Subúmido seco", "#B7D89A"),
    ("area_umida2021_per", "Úmido", "#2E75B6"),
)


def gerar_grafico_aridez(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    labels = []
    valores = []
    cores = []
    for campo, rotulo, cor in _CATEGORIAS_ARIDEZ:
        valor = cidade.get(campo)
        if valor is None:
            continue
        labels.append(rotulo)
        valores.append(float(valor))
        cores.append(cor)

    if not valores:
        raise ValueError("Dados de classificação de aridez não disponíveis.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_aridez_{safe_city}.png"

    # Eixo (e barra) travados em 0-100%: é um percentual da área municipal,
    # então a escala não deve variar por cidade. Pequenos excessos de
    # arredondamento da view (ex.: soma das classes dando 100,2%) não devem
    # desenhar a barra acima da linha de 100% — o rótulo mostra o valor real,
    # só a altura desenhada é que fica limitada.
    limite_eixo = 100.0
    alturas_barra = [min(valor, limite_eixo) for valor in valores]

    fig, ax = plt.subplots(figsize=(6.1, 4.05))
    x = np.arange(len(labels))
    barras = ax.bar(x, alturas_barra, width=0.6, color=cores, zorder=3)

    margem_label = limite_eixo * 0.06
    ax.set_ylim(0, limite_eixo + margem_label)
    ax.set_yticks([0, 25, 50, 75, 100])

    for barra, valor in zip(barras, valores):
        ax.text(
            barra.get_x() + barra.get_width() / 2,
            barra.get_height() + limite_eixo * 0.02,
            f"{valor:.1f}%".replace(".", ","),
            ha="center",
            va="bottom",
            fontsize=10 * ESCALA_FONTE,
            fontweight=600,
            color="#514C50",
        )

    ax.set_xticks([])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda valor, _: f"{valor:.0f}%"))
    ax.grid(axis="y", linestyle=(0, (1, 4)), linewidth=0.8, color="#D9D9D9", zorder=0)
    ax.tick_params(axis="both", length=0, colors="#514C50", labelsize=9 * ESCALA_FONTE)
    for lado in ("left", "right", "bottom", "top"):
        ax.spines[lado].set_visible(False)
    ax.margins(x=0.18)

    marcadores_legenda = [
        Line2D([0], [0], marker="o", linestyle="", markersize=9, color=cor)
        for cor in cores
    ]
    ax.legend(
        marcadores_legenda,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.04),
        ncol=len(labels),
        frameon=False,
        fontsize=9 * ESCALA_FONTE,
        handletextpad=0.4,
        columnspacing=1.2,
    )

    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    plt.tight_layout(pad=1.2)
    plt.savefig(chart_file, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return chart_file.name
