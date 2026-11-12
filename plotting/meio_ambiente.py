import pathlib

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter

from plotting import (
    ESCALA_FONTE,
    FONTE_ROTULO_EIXO,
    FONTE_ROTULO_VALOR,
    FONTE_TICK,
    iniciar_card_grafico,
    reusar_grafico,
    salvar_card_grafico,
)

# (campo no contexto, rótulo da legenda, cor) — ordem e cores espelham o Doc.
# Campos vêm de relatorios_auto.ambiente (percentual da área municipal em
# cada classe de aridez, ano de 2021).
_CATEGORIAS_ARIDEZ = (
    ("area_arida2021_per", "Árido", "#C0392B"),
    ("area_semiarida2021_per", "Semiárido", "#E67E22"),
    ("area_subumida2021_per", "Subúmido seco", "#B7D89A"),
    ("area_umida2021_per", "Úmido", "#2E75B6"),
    ("area_sem_dados2021_per", "Sem dados", "#B0B0B0"),
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
    reuso = reusar_grafico(chart_file)
    if reuso is not None:
        return reuso

    # Eixo (e barra) travados em 0-100%: é um percentual da área municipal,
    # então a escala não deve variar por cidade. Pequenos excessos de
    # arredondamento da view (ex.: soma das classes dando 100,2%) não devem
    # desenhar a barra acima da linha de 100% — o rótulo mostra o valor real,
    # só a altura desenhada é que fica limitada.
    limite_eixo = 100.0
    alturas_barra = [min(valor, limite_eixo) for valor in valores]

    fig, ax = iniciar_card_grafico((6.1, 4.05), "Condições de aridez")
    # Mesmo ajuste do gráfico de IDHM (plotting/desenvolvimento_social.py): a
    # legenda de categorias fica abaixo do eixo (bbox_to_anchor negativo) e,
    # sem espaço reservado, saía cortada pra fora da moldura do card.
    posicao = ax.get_position()
    altura_legenda = posicao.height * 0.16
    ax.set_position(
        (posicao.x0, posicao.y0 + altura_legenda, posicao.width, posicao.height - altura_legenda)
    )

    x = np.arange(len(labels))
    barras = ax.bar(x, alturas_barra, width=0.6, color=cores, zorder=3)

    margem_label = limite_eixo * 0.06
    ax.set_ylim(0, limite_eixo + margem_label)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel("Área municipal", fontsize=FONTE_ROTULO_EIXO * ESCALA_FONTE)

    for barra, valor in zip(barras, valores):
        ax.text(
            barra.get_x() + barra.get_width() / 2,
            barra.get_height() + limite_eixo * 0.02,
            f"{valor:.2f}%".replace(".", ","),
            ha="center",
            va="bottom",
            fontsize=FONTE_ROTULO_VALOR * ESCALA_FONTE,
            fontweight=600,
            color="#514C50",
        )

    ax.set_xticks([])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda valor, _: f"{valor:.0f}%"))
    ax.grid(axis="y", linestyle=(0, (1, 4)), linewidth=0.8, color="#D9D9D9", zorder=0)
    ax.tick_params(axis="both", length=0, colors="#514C50", labelsize=FONTE_TICK * ESCALA_FONTE)
    for lado in ("left", "right", "bottom", "top"):
        ax.spines[lado].set_visible(False)
    ax.margins(x=0.18)

    # Legenda tem largura fixa (card de 6,1"): com 4 categorias (caso histórico)
    # cabe em fontsize=9, mas a 5ª ("Sem dados") estourava a borda do card.
    # Encolhe fonte/espaçamento proporcionalmente acima de 4 rótulos em vez de
    # travar num valor fixo, pra não voltar a quebrar se surgir uma 6ª classe.
    escala_legenda = min(1.0, 4 / len(labels))
    marcadores_legenda = [
        Line2D([0], [0], marker="o", linestyle="", markersize=9 * escala_legenda, color=cor)
        for cor in cores
    ]
    ax.legend(
        marcadores_legenda,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.14),
        ncol=len(labels),
        frameon=False,
        fontsize=9 * ESCALA_FONTE * escala_legenda,
        handletextpad=0.4 * escala_legenda,
        columnspacing=1.2 * escala_legenda,
    )

    salvar_card_grafico(fig, chart_file)
    return chart_file.name


# Gráfico comparado do relatório por estado (12/11/2026): as classes do municipal
# mais a hiperárida, que a matview estadual traz (zerada nos 9 estados nessa data).
_CATEGORIAS_ARIDEZ_COMPARADA = (
    ("area_hiperarida", "Hiperárido", "#7B241C"),
    *((campo.removesuffix("2021_per"), rotulo, cor) for campo, rotulo, cor in _CATEGORIAS_ARIDEZ),
)
_COR_LEGENDA_POR_ANO = {1991: "#C9C6C8", 2021: "#514C50"}
_OPACIDADE_1991 = 0.4


def _anos_da_aridez(cidade: dict) -> tuple[int, ...]:
    if cidade.get("aridez_2021_valida") != 1:
        raise ValueError(
            f"Aridez de 2021 inválida (aridez_2021_valida={cidade.get('aridez_2021_valida')!r}); "
            "esperava 1 para gerar o gráfico comparado."
        )

    return (1991, 2021) if cidade.get("aridez_1991_valida") == 1 else (2021,)


def _percentuais_da_aridez(cidade: dict, anos: tuple[int, ...]) -> list[tuple[str, str, dict[int, float]]]:
    """(rótulo, cor, {ano: %}) das classes com área em algum dos anos."""
    classes = []
    for campo, rotulo, cor in _CATEGORIAS_ARIDEZ_COMPARADA:
        por_ano = {ano: float(cidade.get(f"{campo}{ano}_per") or 0) for ano in anos}
        if any(por_ano.values()):
            classes.append((rotulo, cor, por_ano))

    return classes


def _rotular_barras_da_aridez(ax, barras, valores: list[float], tamanho_fonte: float) -> None:
    for barra, valor in zip(barras, valores):
        ax.text(
            barra.get_x() + barra.get_width() / 2,
            barra.get_height() + 2,
            f"{valor:.2f}%".replace(".", ","),
            ha="center",
            va="bottom",
            fontsize=tamanho_fonte,
            fontweight=600,
            color="#514C50",
        )


def gerar_grafico_aridez_comparada(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    """Percentual da área em cada classe de aridez em 2021 e, quando
    `aridez_1991_valida` é 1, em 1991 (barra mais clara ao lado). Lê
    `area_<classe><ano>_per`; classe sem área nos dois anos fica de fora.

    Pedido pelo Doc estadual de Meio Ambiente (marcador `grafico_aridez_estadual`),
    que compara os dois anos; o municipal (gerar_grafico_aridez) só tem 2021.

    Ex.: gerar_grafico_aridez_comparada(contexto, OUTPUT_DIR, "estado_para_ba")
    """
    anos = _anos_da_aridez(cidade)
    classes = _percentuais_da_aridez(cidade, anos)
    if not classes:
        raise ValueError(f"Nenhuma classe de aridez com área em {anos}.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_aridez_comparada_{safe_city}.png"
    reuso = reusar_grafico(chart_file)
    if reuso is not None:
        return reuso

    fig, ax = iniciar_card_grafico((8, 4.4), "Condições de aridez")
    # Faixa abaixo do eixo para os nomes das classes e a legenda dos anos.
    posicao = ax.get_position()
    altura_legenda = posicao.height * 0.2
    ax.set_position(
        (posicao.x0, posicao.y0 + altura_legenda, posicao.width, posicao.height - altura_legenda)
    )

    x = np.arange(len(classes))
    largura = 0.8 / len(anos)
    tamanho_rotulo = FONTE_ROTULO_VALOR * ESCALA_FONTE * (0.8 if len(anos) > 1 else 1)
    for indice, ano in enumerate(anos):
        deslocamento = (indice - (len(anos) - 1) / 2) * largura
        valores = [por_ano[ano] for _, _, por_ano in classes]
        barras = ax.bar(
            x + deslocamento,
            # Altura travada em 100%, como no municipal: arredondamento da view
            # (100,01%) não desenha a barra acima da linha; o rótulo mostra o real.
            [min(valor, 100.0) for valor in valores],
            width=largura * 0.92,
            color=[cor for _, cor, _ in classes],
            alpha=_OPACIDADE_1991 if ano == 1991 else 1,
            zorder=3,
        )
        _rotular_barras_da_aridez(ax, barras, valores, tamanho_rotulo)

    ax.set_ylim(0, 112)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel("Área do estado", fontsize=FONTE_ROTULO_EIXO * ESCALA_FONTE)
    ax.set_xticks(x)
    ax.set_xticklabels([rotulo for rotulo, _, _ in classes], fontsize=FONTE_TICK * ESCALA_FONTE)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda valor, _: f"{valor:.0f}%"))
    ax.grid(axis="y", linestyle=(0, (1, 4)), linewidth=0.8, color="#D9D9D9", zorder=0)
    ax.tick_params(axis="both", length=0, colors="#514C50", labelsize=FONTE_TICK * ESCALA_FONTE)
    for lado in ("left", "right", "bottom", "top"):
        ax.spines[lado].set_visible(False)

    if len(anos) > 1:
        marcadores = [
            Line2D([0], [0], marker="s", linestyle="", markersize=9, color=_COR_LEGENDA_POR_ANO[ano])
            for ano in anos
        ]
        ax.legend(
            marcadores,
            [str(ano) for ano in anos],
            loc="upper center",
            bbox_to_anchor=(0.5, -0.16),
            ncol=len(anos),
            frameon=False,
            fontsize=9 * ESCALA_FONTE,
        )

    salvar_card_grafico(fig, chart_file)
    return chart_file.name
