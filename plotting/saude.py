import math
import pathlib

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter


def _coerce_numero(valor) -> float:
    if valor is None:
        return 0.0

    if isinstance(valor, str):
        valor = valor.strip().replace(",", ".")

    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return 0.0

    if not math.isfinite(numero):
        return 0.0

    return numero


def gerar_grafico_publico_etario(
    cidade,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
):
    categorias = [
        "Ao nascer",
        "Menores de 1 ano",
        "1 ano de idade",
        "Multifaixa etária",
    ]

    publico_alvo = [
        _coerce_numero(cidade["publico_etario_ao_nascer"]),
        _coerce_numero(cidade["publico_etario_menor_1_ano"]),
        _coerce_numero(cidade["publico_etario_1_ano"]),
        _coerce_numero(cidade["publico_etario_multifaixa"]),
    ]

    doses_aplicadas = [
        _coerce_numero(cidade["dose_etario_ao_nascer"]),
        _coerce_numero(cidade["dose_etario_menor_1_ano"]),
        _coerce_numero(cidade["dose_etario_1_ano"]),
        _coerce_numero(cidade["dose_etario_multifaixa"]),
    ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    chart_file = (
        OUTPUT_DIR
        / f"grafico_publico_etario_{safe_city}.png"
    )

    # Posição dos grupos no eixo X
    x = np.arange(len(categorias))

    # Largura das barras
    largura = 0.30

    _fig, ax = plt.subplots(figsize=(8, 3.2))

    ax.bar(
        x - largura / 2,
        publico_alvo,
        width=largura,
        label="Público-alvo",
        color="#FF9AA2",
    )

    ax.bar(
        x + largura / 2,
        doses_aplicadas,
        width=largura,
        label="Doses aplicadas",
        color="#FF5A6E",
    )

    # Eixo X
    ax.set_xticks(x)
    ax.set_xticklabels(
        categorias,
        fontsize=8,
    )

    # Eixo Y
    ax.set_ylabel("")

    valor_maximo = max([*publico_alvo, *doses_aplicadas])
    ax.set_ylim(0, max(valor_maximo * 1.15, 10))

    ax.yaxis.set_major_formatter(
        FuncFormatter(
            lambda valor, posicao: f"{valor / 1000:g} mil"
            if valor >= 1000
            else f"{valor:g}"
        )
    )

    # Grade horizontal
    ax.yaxis.grid(
        True,
        linestyle="--",
        linewidth=0.5,
        alpha=0.25,
    )

    ax.set_axisbelow(True)

    # Remove bordas
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    # Remove ticks
    ax.tick_params(
        axis="both",
        length=0,
        labelsize=8,
    )

    # Legenda
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.20),
        ncol=2,
        frameon=False,
        fontsize=8,
    )

    ax.set_xlabel(
        "Público-alvo etário",
        fontsize=9,
    )

    plt.tight_layout()

    plt.savefig(
        chart_file,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close()

    return chart_file.name