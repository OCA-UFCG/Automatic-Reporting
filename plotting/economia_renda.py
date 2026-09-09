import pathlib

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from plotting.hidraulica import _numero
from utils.queries.economia_renda import _escalar_valor

_COR_LINHA = "#F0883E"


def _escolher_unidade(valor: float) -> tuple[float, str]:
    _, unidade = _escalar_valor(valor)
    divisor = {"bilhões": 1e9, "milhões": 1e6, "mil": 1e3}.get(unidade, 1)
    return divisor, unidade


def gerar_grafico_pib(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    serie = cidade.get("pib_serie") or []
    pontos = [
        (item["ano"], _numero(item.get("pib_total")))
        for item in serie
        if item.get("ano") is not None and item.get("pib_total") is not None
    ]
    if not pontos:
        raise ValueError("Dados anuais de PIB total não disponíveis.")

    anos = [ano for ano, _ in pontos]
    valores = [valor for _, valor in pontos]
    divisor_eixo, unidade_eixo = _escolher_unidade(max(valores))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_pib_{safe_city}.png"

    fig, ax = plt.subplots(figsize=(10, 4.5))

    ax.plot(
        anos,
        valores,
        linestyle=":",
        marker="o",
        linewidth=2,
        markersize=5,
        color=_COR_LINHA,
        markerfacecolor=_COR_LINHA,
        markeredgecolor=_COR_LINHA,
    )

    for ano, valor in zip(anos, valores):
        divisor_ponto, unidade_ponto = _escolher_unidade(valor)
        sufixo_ponto = f" {unidade_ponto}" if unidade_ponto else ""
        ax.annotate(
            f"R$ {valor / divisor_ponto:.1f}{sufixo_ponto}",
            (ano, valor),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color="#4A4A4A",
        )

    ax.set_title(
        "Evolução anual do PIB Total",
        loc="left",
        fontsize=11,
        fontweight="bold",
    )

    valor_minimo = min(valores)
    valor_maximo = max(valores)
    amplitude = valor_maximo - valor_minimo or valor_maximo or 1.0
    margem = amplitude * 0.15
    ax.set_ylim(valor_minimo - margem, valor_maximo + margem)

    ax.set_xticks(anos)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    ax.grid(axis="y", linestyle=":", alpha=0.4)

    sufixo_eixo = f" {unidade_eixo}" if unidade_eixo else ""
    ax.yaxis.set_major_formatter(
        FuncFormatter(lambda valor, _: f"R$ {valor / divisor_eixo:.0f}{sufixo_eixo}")
    )

    fig.tight_layout()
    fig.savefig(chart_file, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return chart_file.name
