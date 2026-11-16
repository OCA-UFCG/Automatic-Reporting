import pathlib
from decimal import ROUND_HALF_UP, Decimal
from functools import partial

import numpy as np
from matplotlib.lines import Line2D

from plotting import (
    ESCALA_FONTE,
    FONTE_ROTULO_VALOR,
    FONTE_TICK,
    iniciar_card_grafico,
    reusar_grafico,
    salvar_card_grafico,
)
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
    reuso = reusar_grafico(chart_file)
    if reuso is not None:
        return reuso

    x = np.arange(len(anos))

    fig, ax = iniciar_card_grafico((8, 4.1), "Evolução do IDHM")
    # Mesmo ajuste do gráfico de faixa etária (plotting/demografia.py): a
    # legenda de categorias fica abaixo do eixo (bbox_to_anchor negativo) e,
    # sem espaço reservado, saía cortada pra fora da moldura do card.
    posicao = ax.get_position()
    altura_legenda = posicao.height * 0.22
    ax.set_position(
        (posicao.x0, posicao.y0 + altura_legenda, posicao.width, posicao.height - altura_legenda)
    )

    barras = ax.bar(x, valores, width=0.5, color=cores, zorder=3)

    limite = max(valores) * 1.22 if valores else 1
    ax.set_ylim(0, limite)

    for barra, valor in zip(barras, valores):
        ax.text(
            barra.get_x() + barra.get_width() / 2,
            valor + limite * 0.025,
            f"{valor:.3f}".replace(".", ","),
            ha="center",
            va="bottom",
            fontsize=FONTE_ROTULO_VALOR*ESCALA_FONTE,
            fontweight=600,
            color="#4A4A4A",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(anos, fontsize=FONTE_TICK*ESCALA_FONTE)
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

    ax.tick_params(axis="both", length=0, labelsize=FONTE_TICK*ESCALA_FONTE, colors="#4A4A4A")
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
        fontsize=8*ESCALA_FONTE,
    )

    salvar_card_grafico(fig, chart_file)

    return chart_file.name


# Gráfico de área de desenvolvimento social (16/11/2026): medianas do IDHM e dos
# componentes por ano, em linhas, como a Figura 1 que a equipe mandou no .docx do
# Nordeste. Cor e marcador por série, na ordem da legenda da figura.
_ESTILO_DA_SERIE_IDHM = {
    "IDHM": ("#24513F", "o"),
    "Longevidade": ("#4A7BA7", "s"),
    "Renda": ("#C27F35", "D"),
    "Educação": ("#8A5A6E", "^"),
}
_SERIE_EM_DESTAQUE = "IDHM"


def rotulo_do_indice(valor: float) -> str:
    """Índice com 3 casas e arredondamento comercial, como no texto do Doc. O
    `f"{v:.3f}"` daria "0,757" para 0,7575 (o float fica um pouco abaixo).

    Ex.: rotulo_do_indice(0.7575) == "0,758"
    """
    arredondado = Decimal(str(valor)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    return str(arredondado).replace(".", ",")


def gerar_grafico_idhm_e_componentes(
    anos: tuple[str, ...],
    series: dict[str, tuple[float, ...]],
    output_dir: pathlib.Path,
    safe_nome: str,
) -> str:
    """PNG das medianas do IDHM e dos componentes por ano: o IDHM em destaque,
    rotulado em todos os anos; os componentes rotulados só no último.

    Ex.: gerar_grafico_idhm_e_componentes(("1991", "2010"), {"IDHM": (0.291, 0.588)},
         OUTPUT_DIR, "area_nordeste") == "grafico_idhm_componentes_area_nordeste.png"
    """
    if not series or any(len(valores) != len(anos) for valores in series.values()):
        raise ValueError(f"Séries do IDHM com tamanho diferente dos anos {anos}: {series}")
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_file = output_dir / f"grafico_idhm_componentes_{safe_nome}.png"
    reuso = reusar_grafico(chart_file)
    if reuso is not None:
        return reuso
    fig, ax = iniciar_card_grafico((8, 4.4), "Medianas do IDHM e de seus componentes")
    x = np.arange(len(anos))
    for nome, valores in series.items():
        _desenhar_serie_idhm(ax, x, nome, valores)
    _formatar_eixos_idhm(ax, x, anos)
    salvar_card_grafico(fig, chart_file)

    return chart_file.name


def _desenhar_serie_idhm(ax, x: np.ndarray, nome: str, valores: tuple[float, ...]) -> None:
    cor, marcador = _ESTILO_DA_SERIE_IDHM.get(nome, ("#4A4A4A", "o"))
    destaque = nome == _SERIE_EM_DESTAQUE
    ax.plot(
        x, valores, color=cor, marker=marcador, markersize=7,
        linewidth=3.2 if destaque else 2, label=nome, zorder=5 if destaque else 4,
    )
    if destaque:
        _rotular_serie_em_destaque(ax, x, valores, cor)
        return
    ax.annotate(
        rotulo_do_indice(valores[-1]), (x[-1], valores[-1]), textcoords="offset points",
        xytext=(10, 0), va="center", fontsize=FONTE_ROTULO_VALOR * ESCALA_FONTE, color=cor,
    )


def _rotular_serie_em_destaque(ax, x: np.ndarray, valores: tuple[float, ...], cor: str) -> None:
    """Rótulo abaixo do ponto e, no último ano, acima, como na figura original: em
    cima, o 0,420 de 2000 batia no marcador da Renda (0,477)."""
    for indice, (posicao, valor) in enumerate(zip(x, valores)):
        ultimo = indice == len(valores) - 1
        ax.annotate(
            rotulo_do_indice(valor), (posicao, valor), textcoords="offset points",
            xytext=(0, 12 if ultimo else -14), ha="center", va="bottom" if ultimo else "top",
            fontsize=FONTE_ROTULO_VALOR * ESCALA_FONTE, fontweight=700, color=cor,
        )


def _formatar_eixos_idhm(ax, x: np.ndarray, anos: tuple[str, ...]) -> None:
    ax.set_xticks(x)
    ax.set_xticklabels(anos)
    ax.set_xlim(-0.3, len(anos) - 1 + 0.45)
    ax.set_ylim(0, 1)
    ax.set_yticks(np.arange(0, 1.01, 0.2))
    ax.set_yticklabels([f"{v:.1f}".replace(".", ",") for v in np.arange(0, 1.01, 0.2)])
    ax.set_ylabel("Mediana dos índices municipais", fontsize=FONTE_TICK * ESCALA_FONTE, color="#4A4A4A")
    ax.grid(axis="y", color="#E5E5E5", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", length=0, labelsize=FONTE_TICK * ESCALA_FONTE, colors="#4A4A4A")
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color("#B0B0B0")
    ax.legend(
        loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=len(_ESTILO_DA_SERIE_IDHM),
        frameon=False, fontsize=9 * ESCALA_FONTE,
    )
