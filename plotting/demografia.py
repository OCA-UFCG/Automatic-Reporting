import pathlib

import matplotlib.pyplot as plt
import numpy as np

from plotting import ESCALA_FONTE, iniciar_card_grafico, salvar_card_grafico


def _salvar_figura_com_fundo_branco(
    fig, ax, chart_file: pathlib.Path, pad: float | None = None
) -> None:
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    plt.tight_layout() if pad is None else plt.tight_layout(pad=pad)
    plt.savefig(chart_file, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def gerar_grafico_faixa_etaria_e_sexo(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    faixas = cidade.get("faixas_etarias_sexo") or []
    if not faixas:
        raise ValueError("Dados por faixa etária e sexo não disponíveis.")

    labels = [str(item["faixa"]) for item in faixas]
    mulheres = np.array([float(item["mulheres"] or 0) for item in faixas])
    homens = np.array([float(item["homens"] or 0) for item in faixas])
    y = np.arange(len(labels))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_faixa_etaria_e_sexo_{safe_city}.png"

    fig, ax = iniciar_card_grafico((8, 5.6), "População por faixa etária e sexo")
    # Reserva uma faixa abaixo do corpo do gráfico, dentro do card, para a
    # legenda (senão ela cai fora da área desenhada e some do PNG).
    posicao = ax.get_position()
    altura_legenda = posicao.height * 0.12
    ax.set_position(
        (posicao.x0, posicao.y0 + altura_legenda, posicao.width, posicao.height - altura_legenda)
    )
    ax.barh(y, -mulheres, height=0.86, color="#C92F67", label="Mulheres")
    ax.barh(y, homens, height=0.86, color="#8DB52B", label="Homens")

    limite = max(float(mulheres.max()), float(homens.max()), 1.0)
    margem_rotulo = limite * 0.035
    for indice, (valor_mulheres, valor_homens) in enumerate(zip(mulheres, homens)):
        rotulo_mulheres = f"{valor_mulheres:,.0f}".replace(",", ".")
        rotulo_homens = f"{valor_homens:,.0f}".replace(",", ".")
        ax.text(-valor_mulheres - margem_rotulo, indice, rotulo_mulheres,
                ha="right", va="center", fontsize=9*ESCALA_FONTE, color="#292829")
        ax.text(valor_homens + margem_rotulo, indice, rotulo_homens,
                ha="left", va="center", fontsize=9*ESCALA_FONTE, color="#292829")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9*ESCALA_FONTE)
    ax.axvline(0, color="#FFFFFF", linewidth=1.5)
    ax.set_xlim(-limite * 1.38, limite * 1.38)
    ax.set_xticks([])
    ax.tick_params(axis="y", length=0, pad=8)
    for borda in ax.spines.values():
        borda.set_visible(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=2,
              frameon=False, fontsize=9*ESCALA_FONTE)
    salvar_card_grafico(fig, chart_file)
    return chart_file.name


_ROTULOS_COR_RACA = {
    "branca": "Branca",
    "preta": "Preta",
    "parda": "Parda",
    "amarela": "Amarela",
    "indigena": "Indígena",
}

_CORES_COR_RACA = {
    "branca": "#D97AAA",
    "preta": "#514C50",
    "parda": "#C9A227",
    "amarela": "#8DB52B",
    "indigena": "#2F9E8F",
}


def gerar_grafico_composicao_cor_raca(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    racas = {
        cor: float(cidade.get(f"pop_{cor}") or 0) for cor in _ROTULOS_COR_RACA
    }
    total = sum(racas.values())
    if not total:
        raise ValueError("Dados de composição por cor ou raça não disponíveis.")

    itens = sorted(racas.items(), key=lambda item: item[1], reverse=True)
    labels = [_ROTULOS_COR_RACA[cor] for cor, _ in itens]
    percentuais = [valor / total * 100 for _, valor in itens]
    cores = [_CORES_COR_RACA[cor] for cor, _ in itens]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_composicao_cor_raca_{safe_city}.png"

    fig, ax = iniciar_card_grafico((6.4, 4.3), "Composição por cor ou raça")

    # Maior percentual no topo, como na lista do card (barras horizontais).
    y = np.arange(len(labels))[::-1]
    ax.barh(y, percentuais, height=0.56, color=cores, zorder=3)

    limite = max(percentuais) * 1.3 if percentuais else 1
    ax.set_xlim(0, limite)
    ax.set_ylim(-0.7, len(labels) - 0.3)
    for pos_y, percentual in zip(y, percentuais):
        ax.text(
            percentual + limite * 0.02,
            pos_y,
            f"{percentual:.1f}%".replace(".", ","),
            ha="left",
            va="center",
            fontsize=10*ESCALA_FONTE,
            fontweight=600,
            color="#292829",
        )

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10*ESCALA_FONTE, fontweight=600, color="#292829")
    ax.set_xticks([])
    ax.tick_params(axis="y", length=0, pad=10)
    for borda in ax.spines.values():
        borda.set_visible(False)
    salvar_card_grafico(fig, chart_file)
    return chart_file.name
