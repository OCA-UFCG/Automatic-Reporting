import pathlib

import numpy as np
from matplotlib.ticker import FuncFormatter, MaxNLocator

from plotting import (
    ESCALA_FONTE,
    ajustar_margem_esquerda_para_rotulos,
    iniciar_card_grafico,
    salvar_card_grafico,
)
from utils.formatting import coerce_para_float as _coerce_numero


def _reservar_espaco_rotulo_x(fig, ax, reserva_polegadas: float = 0.34) -> None:
    # `iniciar_card_grafico` posiciona o corpo do card sem folga para um
    # `ax.set_xlabel`: o texto cai abaixo da moldura e some do PNG. Encolhe o
    # eixo (mesmo truque usado pra legenda em demografia.py) reservando uma
    # faixa fixa, em polegadas, na base do card.
    altura_fig = fig.get_size_inches()[1]
    fracao = reserva_polegadas / altura_fig
    posicao = ax.get_position()
    ax.set_position(
        (posicao.x0, posicao.y0 + fracao, posicao.width, posicao.height - fracao)
    )


def _rotular_barra_vertical(ax, barra, texto: str, limite: float) -> None:
    altura = barra.get_height()
    pequena = altura < limite * 0.15
    ax.text(
        barra.get_x() + barra.get_width() / 2,
        altura + limite * 0.05 if pequena else altura - limite * 0.05,
        texto,
        ha="center",
        va="bottom" if pequena else "top",
        fontsize=11*ESCALA_FONTE,
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

    fig, ax = iniciar_card_grafico(
        (10, 4.4), "Visão histórica da taxa de mortalidade infantil"
    )
    _reservar_espaco_rotulo_x(fig, ax, reserva_polegadas=0.5)

    barras = ax.bar(x, taxas, width=0.62, color="#9E2A3F", zorder=3)

    limite = max(max(taxas, default=0) * 1.25, 10)
    ax.set_ylim(0, limite)

    for barra, taxa in zip(barras, taxas):
        _rotular_barra_vertical(
            ax, barra, f"{taxa:.2f}".replace(".", ","), limite
        )

    ax.set_xticks(x)
    ax.set_xticklabels(anos, fontsize=11*ESCALA_FONTE)
    ax.set_xlabel("Ano", fontsize=12*ESCALA_FONTE)

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

    ax.tick_params(axis="both", length=0, labelsize=11*ESCALA_FONTE, colors="#4A4A4A")

    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color("#4A4A4A")

    salvar_card_grafico(fig, chart_file)

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

    fig, ax = iniciar_card_grafico(
        (10, 4.4), "Visão histórica do número de estabelecimentos de saúde"
    )
    _reservar_espaco_rotulo_x(fig, ax, reserva_polegadas=0.5)

    barras = ax.bar(x, totais, width=0.62, color="#FF5A6E", zorder=3)

    limite = max(max(totais, default=0) * 1.25, 10)
    ax.set_ylim(0, limite)

    for barra, total in zip(barras, totais):
        _rotular_barra_vertical(ax, barra, _formatar_valor_mil(total), limite)

    ax.set_xticks(x)
    ax.set_xticklabels(anos, fontsize=11*ESCALA_FONTE)
    ax.set_xlabel("Ano", fontsize=12*ESCALA_FONTE)

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

    ax.tick_params(axis="both", length=0, labelsize=11*ESCALA_FONTE, colors="#4A4A4A")

    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color("#4A4A4A")

    salvar_card_grafico(fig, chart_file)

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

    altura = max(4.2, 0.55 * len(vacinas) + 1.2)
    # Faixa de header proporcionalmente menor em cards mais altos (muitas
    # vacinas), senão o título fica desproporcionalmente grande no topo.
    altura_header = min(0.14, 3.6 * 0.14 / altura)
    fig, ax = iniciar_card_grafico(
        (11, altura),
        "Taxa de cobertura vacinal por tipo de vacina",
        altura_header=altura_header,
        margem_direita=0.09,
    )
    _reservar_espaco_rotulo_x(fig, ax)

    y = np.arange(len(vacinas))

    ax.barh(y, coberturas, height=0.5, color="#FF5A6E", zorder=3)

    ax.set_yticks(y)
    ax.set_yticklabels(vacinas, fontsize=11*ESCALA_FONTE)
    ax.invert_yaxis()

    ax.set_ylabel("Imunobiológico", fontsize=12*ESCALA_FONTE)
    # Nomes de vacina variam muito de tamanho (de "BCG" a "Pentavalente
    # (DTP/Hib/HepB)"); a margem esquerda fixa do card não dá conta dos mais
    # longos e eles saem cortados pra fora da moldura — mede o rótulo mais
    # largo já desenhado e expande a margem até caber. Precisa rodar depois do
    # `set_ylabel` acima: a função só reserva espaço e fixa a posição do rótulo
    # se ele já existir, senão o posicionamento automático do matplotlib some
    # com o texto (fica fora do canvas) quando o `set_ylabel` roda depois.
    ajustar_margem_esquerda_para_rotulos(fig, ax)

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
            fontsize=10.5*ESCALA_FONTE,
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

    ax.tick_params(axis="both", length=0, labelsize=11*ESCALA_FONTE, colors="#4A4A4A")

    ax.set_xlabel("Taxa de cobertura vacinal (%)", fontsize=12*ESCALA_FONTE)

    salvar_card_grafico(fig, chart_file)

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

    fig, ax = iniciar_card_grafico((10, 4.6), "Público-alvo etário e doses aplicadas")
    # A legenda fica abaixo do eixo (bbox_to_anchor negativo); sem encolher o
    # `ax` ela cai fora da área desenhada e sai cortada do card.
    posicao = ax.get_position()
    altura_legenda = posicao.height * 0.34
    ax.set_position(
        (posicao.x0, posicao.y0 + altura_legenda, posicao.width, posicao.height - altura_legenda)
    )

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
        fontsize=11*ESCALA_FONTE,
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
        labelsize=11*ESCALA_FONTE,
    )

    # Legenda
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.20),
        ncol=2,
        frameon=False,
        fontsize=11*ESCALA_FONTE,
    )

    ax.set_xlabel(
        "Público-alvo etário",
        fontsize=12*ESCALA_FONTE,
    )

    salvar_card_grafico(fig, chart_file)

    return chart_file.name