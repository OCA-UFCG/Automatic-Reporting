import math
import pathlib

import numpy as np
from matplotlib.ticker import FuncFormatter, MaxNLocator

from plotting import ESCALA_FONTE, iniciar_card_grafico, salvar_card_grafico


def _numero(valor: object) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return 0.0
    return numero if math.isfinite(numero) else 0.0


def _formatar_inteiro(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def gerar_grafico_tecnologias_acesso_agua(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    serie = cidade.get("tecnologias_acesso_agua_serie") or []
    pontos = [
        (str(item["ano"]), _numero(item.get("total")))
        for item in serie
        if item.get("ano") is not None
    ]
    if not pontos:
        raise ValueError("Dados anuais de tecnologias de acesso à água não disponíveis.")

    anos = [ano for ano, _ in pontos]
    totais = [total for _, total in pontos]
    x = np.arange(len(anos))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_tecnologias_acesso_agua_{safe_city}.png"

    fig, ax = iniciar_card_grafico(
        (8, 4.0), "Tecnologias de acesso à água ao longo dos anos"
    )
    # Reserva uma faixa abaixo do corpo do gráfico, dentro do card, para o
    # rótulo "Ano" (senão ele fica colado/cortado na borda inferior do card).
    posicao = ax.get_position()
    altura_rotulo_x = posicao.height * 0.12
    ax.set_position(
        (posicao.x0, posicao.y0 + altura_rotulo_x, posicao.width, posicao.height - altura_rotulo_x)
    )

    barras = ax.bar(x, totais, width=0.78, color="#2098BD", zorder=3)
    limite = max(max(totais, default=0) * 1.22, 10)
    ax.set_ylim(0, limite)

    for barra, total in zip(barras, totais):
        ax.text(
            barra.get_x() + barra.get_width() / 2,
            total + limite * 0.025,
            _formatar_inteiro(total),
            ha="center",
            va="bottom",
            fontsize=8*ESCALA_FONTE,
            color="#3F3F3F",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(anos, fontsize=8*ESCALA_FONTE)
    ax.set_xlabel("Ano", fontsize=8*ESCALA_FONTE)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda valor, _: _formatar_inteiro(valor)))
    ax.grid(axis="y", linestyle=(0, (2, 3)), linewidth=0.7, color="#D9D9D9", zorder=0)
    ax.tick_params(axis="both", length=0, labelsize=8*ESCALA_FONTE, colors="#4A4A4A")
    for borda in ax.spines.values():
        borda.set_visible(False)

    salvar_card_grafico(fig, chart_file)
    return chart_file.name
