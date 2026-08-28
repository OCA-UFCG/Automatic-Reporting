import math
import pathlib

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter, MaxNLocator


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


def _finalizar_grafico(fig, chart_file: pathlib.Path) -> None:
    plt.tight_layout()
    plt.savefig(chart_file, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _rotular_barra_vertical(ax, barra, texto: str, limite: float) -> None:
    altura = barra.get_height()
    pequena = altura < limite * 0.15
    ax.text(
        barra.get_x() + barra.get_width() / 2,
        altura + limite * 0.05 if pequena else altura - limite * 0.05,
        texto,
        ha="center",
        va="bottom" if pequena else "top",
        fontsize=8,
        fontweight="bold",
        color="#4A4A4A" if pequena else "white",
    )


def gerar_grafico_mortalidade_infantil(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    serie = cidade.get("mortalidade_infantil_serie") or []

    pontos = [
        (str(item["ano"]), _coerce_numero(item.get("taxa_mortalidade")))
        for item in serie
        if item.get("ano") is not None
    ]
    if not pontos:
        raise ValueError("Dados históricos de mortalidade infantil não disponíveis.")

    anos = [ano for ano, _ in pontos]
    taxas = [taxa for _, taxa in pontos]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    chart_file = OUTPUT_DIR / f"grafico_mortalidade_infantil_{safe_city}.png"

    x = np.arange(len(anos))

    fig, ax = plt.subplots(figsize=(8, 3.2))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    barras = ax.bar(x, taxas, width=0.62, color="#9E2A3F", zorder=3)

    limite = max(max(taxas, default=0) * 1.25, 10)
    ax.set_ylim(0, limite)

    for barra, taxa in zip(barras, taxas):
        _rotular_barra_vertical(
            ax, barra, f"{taxa:.2f}".replace(".", ","), limite
        )

    ax.set_xticks(x)
    ax.set_xticklabels(anos, fontsize=8)

    ax.yaxis.set_major_locator(MaxNLocator(nbins=3, integer=True))
    ax.grid(
        axis="y",
        linestyle="--",
        linewidth=0.5,
        color="#D9D9D9",
        alpha=0.6,
        zorder=0,
    )
    ax.set_axisbelow(True)

    ax.tick_params(axis="both", length=0, labelsize=8, colors="#4A4A4A")

    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color("#4A4A4A")

    _finalizar_grafico(fig, chart_file)

    return chart_file.name


def _formatar_valor_mil(valor: float) -> str:
    if valor >= 1000:
        texto = f"{valor / 1000:.1f}".rstrip("0").rstrip(".").replace(".", ",")
        return f"{texto} Mil"
    return f"{valor:g}"


def gerar_grafico_de_estabelecimento(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    serie = cidade.get("estabelecimentos_saude_serie") or []

    pontos = [
        (str(item["ano"]), _coerce_numero(item.get("total_estabelecimentos")))
        for item in serie
        if item.get("ano") is not None
    ]
    if not pontos:
        raise ValueError("Dados históricos de estabelecimentos de saúde não disponíveis.")

    anos = [ano for ano, _ in pontos]
    totais = [total for _, total in pontos]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    chart_file = OUTPUT_DIR / f"grafico_de_estabelecimento_{safe_city}.png"

    x = np.arange(len(anos))

    fig, ax = plt.subplots(figsize=(8, 3.2))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    barras = ax.bar(x, totais, width=0.62, color="#FF5A6E", zorder=3)

    limite = max(max(totais, default=0) * 1.25, 10)
    ax.set_ylim(0, limite)

    for barra, total in zip(barras, totais):
        _rotular_barra_vertical(ax, barra, _formatar_valor_mil(total), limite)

    ax.set_xticks(x)
    ax.set_xticklabels(anos, fontsize=8)
    ax.set_xlabel("Ano", fontsize=9)

    ax.yaxis.set_major_formatter(FuncFormatter(lambda valor, _: _formatar_valor_mil(valor)))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=3))

    ax.grid(
        axis="y",
        linestyle="--",
        linewidth=0.5,
        color="#D9D9D9",
        alpha=0.6,
        zorder=0,
    )
    ax.set_axisbelow(True)

    ax.tick_params(axis="both", length=0, labelsize=8, colors="#4A4A4A")

    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color("#4A4A4A")

    _finalizar_grafico(fig, chart_file)

    return chart_file.name


def gerar_grafico_cobertura_vacinal(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    serie = cidade.get("cobertura_vacinal_serie") or []

    dados = [
        (str(item["vacina"]), _coerce_numero(item.get("cobertura_vacinal")))
        for item in serie
        if item.get("vacina") is not None
    ]
    if not dados:
        raise ValueError("Dados de cobertura vacinal não disponíveis.")

    dados.sort(key=lambda item: item[1], reverse=True)

    vacinas = [nome for nome, _ in dados]
    coberturas = [valor for _, valor in dados]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    chart_file = OUTPUT_DIR / f"grafico_cobertura_vacinal_{safe_city}.png"

    altura = max(3.2, 0.34 * len(vacinas) + 0.8)
    fig, ax = plt.subplots(figsize=(8, altura))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    y = np.arange(len(vacinas))

    ax.barh(y, coberturas, height=0.62, color="#FF5A6E", zorder=3)

    ax.set_yticks(y)
    ax.set_yticklabels(vacinas, fontsize=8)
    ax.invert_yaxis()

    limite_superior = max(110.0, max(coberturas) * 1.08)
    ax.set_xlim(0, limite_superior)

    ax.xaxis.set_major_formatter(FuncFormatter(lambda valor, _: f"{valor:g}%"))

    ax.axvline(100, color="#E4444C", linestyle="--", linewidth=1, zorder=2)

    for indice, valor in enumerate(coberturas):
        ax.text(
            valor + limite_superior * 0.012,
            indice,
            f"{valor:.2f}".replace(".", ",") + "%",
            va="center",
            ha="left",
            fontsize=7.5,
            color="#3F3F3F",
        )

    ax.grid(
        axis="x",
        linestyle="--",
        linewidth=0.5,
        alpha=0.25,
        zorder=0,
    )
    ax.set_axisbelow(True)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    ax.tick_params(axis="both", length=0, labelsize=8, colors="#4A4A4A")

    ax.set_xlabel("Taxa de cobertura vacinal (%)", fontsize=9)
    ax.set_ylabel("Imunobiológico", fontsize=9)

    _finalizar_grafico(fig, chart_file)

    return chart_file.name


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

    fig, ax = plt.subplots(figsize=(8, 3.2))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

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
        facecolor="white",
    )

    plt.close(fig)

    return chart_file.name