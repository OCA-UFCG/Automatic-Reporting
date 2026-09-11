import math
import pathlib

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter, MaxNLocator

from plotting import ESCALA_FONTE
from plotting.demografia import _salvar_figura_com_fundo_branco

# (chave no contexto, rótulo da legenda, cor) — ordem e cores espelham o Doc.
_CATEGORIAS = (
    ("esg_rede_geral_ou_pluvial", "Rede geral ou pluvial", "#5B8DEF"),
    ("esg_fossa_septica_ou_fossa_filtro", "Fossa séptica ou fossa filtro", "#AFCBFF"),
    ("esg_fossa_rudimentar_ou_buraco", "Fossa rudimentar ou buraco", "#F6B26B"),
    ("esg_vala", "Vala", "#E8862E"),
    ("esg_rio_lago_corrego_ou_mar", "Rio, lago, córrego ou mar", "#CC4B3C"),
    ("esg_outra_forma", "Outra forma", "#8A8F98"),
    ("esg_nao_tinham_banheiro", "Não tinham banheiro e/ou sanitário", "#8E1B14"),
)


def _numero(valor: object) -> float:
    if isinstance(valor, str):
        valor = valor.strip().replace(".", "").replace(",", ".")
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return 0.0
    return numero if math.isfinite(numero) else 0.0


def _formatar_total(total: float) -> str:
    if total >= 10000:
        return f"{round(total / 1000)} Mil"
    return f"{total:,.0f}".replace(",", ".")


def gerar_grafico_esgotamento_sanitario(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    valores = [_numero(cidade.get(chave)) for chave, _, _ in _CATEGORIAS]
    total = _numero(cidade.get("esg_total")) or sum(valores)
    if total <= 0 or not any(valores):
        raise ValueError("Dados de esgotamento sanitário não disponíveis.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_esgotamento_sanitario_{safe_city}.png"

    rotulos = [rotulo for _, rotulo, _ in _CATEGORIAS]
    cores = [cor for _, _, cor in _CATEGORIAS]

    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_facecolor("white")

    # Rótulo de % só nas fatias >= 2%: as menores ficam quase do mesmo tamanho
    # e seus rótulos se sobreporiam no anel — a categoria delas vai na legenda.
    def _autopct(pct: float) -> str:
        return f"{pct:.1f}%".replace(".", ",") if pct >= 2 else ""

    wedges, _textos, autotextos = ax.pie(
        valores,
        colors=cores,
        startangle=90,
        counterclock=False,
        autopct=_autopct,
        pctdistance=1.18,
        wedgeprops={"width": 0.42, "edgecolor": "white", "linewidth": 1.5},
    )
    for autotexto in autotextos:
        autotexto.set_fontsize(8)
        autotexto.set_color("#4A4A4A")

    ax.text(0, 0.12, _formatar_total(total), ha="center", va="center",
            fontsize=22*ESCALA_FONTE, fontweight="bold", color="#3F3F3F")
    ax.text(0, -0.18, "domicílios", ha="center", va="center",
            fontsize=10*ESCALA_FONTE, color="#6B6B6B")

    ax.legend(
        wedges,
        rotulos,
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=False,
        fontsize=8.5*ESCALA_FONTE,
        handlelength=1.0,
        labelspacing=0.7,
    )
    ax.set_aspect("equal")

    plt.savefig(chart_file, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return chart_file.name


def _rotular_barra_percentual(ax, barra, valor: float, limite: float) -> None:
    ax.text(
        barra.get_x() + barra.get_width() / 2,
        barra.get_height() + limite * 0.03,
        f"{valor:.1f}".replace(".", ",") + "%",
        ha="center",
        va="bottom",
        fontsize=9.5 * ESCALA_FONTE,
        fontweight="bold",
        color="#4A4A4A",
    )


def _grafico_evolucao_percentual(pontos: list[tuple[str, float]], chart_file: pathlib.Path) -> None:
    anos = [ano for ano, _ in pontos]
    valores = [valor for _, valor in pontos]
    x = np.arange(len(anos))

    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.set_facecolor("white")

    barras = ax.bar(x, valores, width=0.5, color="#5B8DEF", zorder=3)

    limite = max(max(valores, default=0) * 1.25, 10)
    ax.set_ylim(0, limite)

    for barra, valor in zip(barras, valores):
        _rotular_barra_percentual(ax, barra, valor, limite)

    ax.set_xticks(x)
    ax.set_xticklabels(anos, fontsize=9 * ESCALA_FONTE)
    ax.set_xlabel("Ano", fontsize=9.5 * ESCALA_FONTE)

    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
    ax.grid(axis="y", linestyle="--", linewidth=0.5, color="#D9D9D9", alpha=0.6, zorder=0)
    ax.set_axisbelow(True)

    ax.tick_params(axis="both", length=0, labelsize=9 * ESCALA_FONTE, colors="#4A4A4A")
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color("#4A4A4A")

    _salvar_figura_com_fundo_branco(fig, ax, chart_file)


def gerar_grafico_evolucao_rede_geral_esgoto(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    pontos = [
        (ano, _numero(cidade.get(chave)))
        for ano, chave in (
            ("2000", "esgoto_rede_2000"),
            ("2010", "esgoto_rede_2010"),
            ("2022", "esgoto_rede_2022"),
        )
        if cidade.get(chave) is not None
    ]
    if not pontos:
        raise ValueError(
            "Dados de evolução da rede geral de esgoto não disponíveis."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_evolucao_rede_geral_esgoto_{safe_city}.png"
    _grafico_evolucao_percentual(pontos, chart_file)
    return chart_file.name


def gerar_grafico_evolucao_coleta_lixo(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    pontos = [
        (ano, _numero(cidade.get(chave)))
        for ano, chave in (
            ("2010", "coleta_2010"),
            ("2022", "coleta_2022"),
        )
        if cidade.get(chave) is not None
    ]
    if not pontos:
        raise ValueError("Dados de evolução da coleta de lixo não disponíveis.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_evolucao_coleta_lixo_{safe_city}.png"
    _grafico_evolucao_percentual(pontos, chart_file)
    return chart_file.name
