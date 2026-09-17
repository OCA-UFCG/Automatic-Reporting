"""Setup compartilhado dos gráficos matplotlib.

Roda uma vez no primeiro import de qualquer ``plotting.*``: registra a fonte
Inter (mesma do relatório HTML) e a torna padrão, para os gráficos casarem com
a tipografia do restante do documento. Sem isso o matplotlib cai no DejaVu Sans.
"""

import logging
import pathlib
from pathlib import Path

import matplotlib

# Antes do primeiro import do pyplot: numa máquina com DISPLAY o matplotlib
# escolheria TkAgg, e os gráficos são gerados numa thread do FastAPI — figura
# Tk fora da main thread trava o processo no teardown.
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.transforms import blended_transform_factory

logger = logging.getLogger(__name__)

_FONTS_DIR = Path(__file__).resolve().parent.parent / "report" / "src" / "styles" / "fonts"
_ARQUIVOS_INTER = (
    "Inter-Regular.ttf",
    "Inter-Medium.ttf",
    "Inter-SemiBold.ttf",
    "Inter-Bold.ttf",
)

# Multiplicador aplicado a todos os tamanhos de fonte dos gráficos (fontsize/
# labelsize). Preserva as proporções entre os textos; ajuste este único número
# para deixar os rótulos/números maiores ou menores de forma uniforme.
ESCALA_FONTE = 1.0

_CARD_PAD_POLEGADAS = 0.3


def _registrar_inter() -> None:
    faltando = []
    for nome in _ARQUIVOS_INTER:
        caminho = _FONTS_DIR / nome
        if caminho.exists():
            font_manager.fontManager.addfont(str(caminho))
        else:
            faltando.append(nome)
    if faltando:
        # Sem a fonte, o matplotlib usa o default; o relatório ainda gera.
        logger.warning("Fontes Inter ausentes em %s: %s", _FONTS_DIR, faltando)
        return
    rcParams["font.family"] = "Inter"
    # Figma pede peso 500 (Medium) pros textos dos gráficos — título e rótulos
    # (eixos, ticks, legenda). Vira o padrão de todo texto matplotlib; onde um
    # texto específico precisa de outro peso (ex.: valor da barra em negrito),
    # o `fontweight` é passado explicitamente naquela chamada e sobrepõe isso.
    rcParams["font.weight"] = "medium"


_registrar_inter()


# Padrão visual "caixa com cabeçalho" pedido pelo design (Figma): moldura
# arredondada + faixa de título cinza no topo, replicado em todos os
# macrotemas. `iniciar_card_grafico` monta a moldura em coordenadas de figura
# (não de eixos) e devolve o `ax` de conteúdo já posicionado dentro dela, para
# cada `gerar_grafico_*` desenhar por cima normalmente.
_CARD_MARGEM = 0.015
_CARD_COR_BORDA = "#D9D9D9"
_CARD_COR_HEADER = "#E7E7E7"
_CARD_COR_TITULO = "#292829"


def iniciar_card_grafico(
    figsize: tuple[float, float],
    titulo: str,
    altura_header: float = 0.14,
    margem_esquerda: float = 0.16,
    margem_direita: float | None = None,
    tamanho_titulo: float = 11.5,
) -> tuple[Figure, "plt.Axes"]:
    # `margem_esquerda` default (0.16) reserva espaço pra rótulos de
    # categoria no eixo Y (o caso comum). Gráficos sem eixo Y rotulado (ex.:
    # um treemap desenhado direto em coordenadas de eixo 0-1, com
    # `axis("off")`) devem passar um valor bem menor, senão sobra uma faixa
    # em branco à esquerda do card.
    margem = _CARD_MARGEM
    fig = plt.figure(figsize=figsize)
    fig.patch.set_facecolor("white")

    card = FancyBboxPatch(
        (margem, margem),
        1 - 2 * margem,
        1 - 2 * margem,
        boxstyle="round,pad=0,rounding_size=0.05",
        transform=fig.transFigure,
        figure=fig,
        facecolor="white",
        edgecolor=_CARD_COR_BORDA,
        linewidth=1.4,
        zorder=1,
    )
    fig.patches.append(card)

    header = Rectangle(
        (margem, 1 - margem - altura_header),
        1 - 2 * margem,
        altura_header,
        transform=fig.transFigure,
        figure=fig,
        facecolor=_CARD_COR_HEADER,
        edgecolor="none",
        zorder=2,
    )
    header.set_clip_path(card)
    fig.patches.append(header)

    fig.text(
        margem + 0.04,
        1 - margem - altura_header / 2,
        titulo,
        transform=fig.transFigure,
        ha="left",
        va="center",
        fontsize=tamanho_titulo * ESCALA_FONTE,
        fontweight="medium",
        color=_CARD_COR_TITULO,
        zorder=3,
    )

    largura_pol, altura_pol = figsize
    pad_x = _CARD_PAD_POLEGADAS / largura_pol
    pad_y = _CARD_PAD_POLEGADAS / altura_pol

    corpo_esq = margem + margem_esquerda
    corpo_dir = 1 - margem - (pad_x if margem_direita is None else margem_direita)
    corpo_topo = 1 - margem - altura_header - pad_y
    corpo_base = margem + pad_y
    ax = fig.add_axes(
        (corpo_esq, corpo_base, corpo_dir - corpo_esq, corpo_topo - corpo_base)
    )
    ax.set_zorder(3)
    return fig, ax


def ajustar_margem_esquerda_para_rotulos(
    fig: Figure, ax: "plt.Axes", pad_polegadas: float = _CARD_PAD_POLEGADAS
) -> None:
    # `margem_esquerda` de `iniciar_card_grafico` é um valor fixo, pensado
    # pro caso comum; rótulos de categoria mais longos que o previsto (ex.:
    # nomes de vacina) estouram essa margem e saem cortados pra fora do card.
    # Mede a posição real já desenhada dos `yticklabels` (e a do `ylabel`, se
    # houver) e reconstrói o layout à esquerda do zero: [borda do card] ->
    # [ylabel, se houver] -> [yticklabels] -> [eixo].
    if not ax.axison:
        # `ax.axis("off")` (ex.: o treemap do VAB) não remove os
        # yticklabels default do matplotlib ("0.0", "0.2"...) nem some com o
        # bbox deles — só deixa de desenhá-los. Medir esses rótulos
        # "fantasma" aqui deslocaria e encolheria um eixo que já foi
        # posicionado (e cujo conteúdo já foi dimensionado) de propósito sem
        # essa margem.
        return

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    rotulos_tick = ax.get_yticklabels()
    if not rotulos_tick:
        return

    largura_fig_pol = fig.get_size_inches()[0]
    largura_fig_px = largura_fig_pol * fig.dpi
    pad_px = pad_polegadas * fig.dpi
    borda_card_px = _CARD_MARGEM * largura_fig_px
    # Mede o x0 real (borda esquerda desenhada) do rótulo mais à esquerda, e
    # não a largura dele: assim o cálculo já inclui o afastamento do
    # `tick_params(pad=...)`, que fica fora da largura do texto.
    inicio_ticks_px = min(
        r.get_window_extent(renderer=renderer).x0 for r in rotulos_tick
    )

    rotulo_eixo = ax.yaxis.get_label()
    tem_ylabel = bool(rotulo_eixo.get_text())
    largura_ylabel_px = 0.0
    if tem_ylabel:
        # A bbox já vem rotacionada: a faixa que o rótulo em pé ocupa é a
        # `.width`; a `.height` é o comprimento do texto.
        largura_ylabel_px = rotulo_eixo.get_window_extent(renderer=renderer).width

    bloco_ylabel_px = (largura_ylabel_px + pad_px) if tem_ylabel else 0
    inicio_ticks_desejado_px = borda_card_px + pad_px + bloco_ylabel_px

    posicao = ax.get_position()
    deslocamento_px = inicio_ticks_desejado_px - inicio_ticks_px
    if deslocamento_px <= 0:
        return

    deslocamento = deslocamento_px / largura_fig_px
    corpo_esq_necessario = posicao.x0 + deslocamento
    ax.set_position(
        (
            corpo_esq_necessario,
            posicao.y0,
            posicao.width - deslocamento,
            posicao.height,
        )
    )

    if tem_ylabel:
        # Não confia no reflow automático do `ylabel` pra acompanhar esse
        # `set_position` manual: pina a posição direto, centralizada no
        # bloco reservado pra ele logo depois da borda do card.
        transformacao = blended_transform_factory(fig.transFigure, ax.transAxes)
        x_desejado_px = borda_card_px + pad_px
        ax.yaxis.set_label_coords(
            (x_desejado_px + largura_ylabel_px / 2) / largura_fig_px,
            0.5,
            transform=transformacao,
        )
        fig.canvas.draw()
        desvio_px = (
            x_desejado_px
            - rotulo_eixo.get_window_extent(renderer=fig.canvas.get_renderer()).x0
        )
        if abs(desvio_px) > 0.5:
            ax.yaxis.set_label_coords(
                (x_desejado_px + largura_ylabel_px / 2 + desvio_px) / largura_fig_px,
                0.5,
                transform=transformacao,
            )


def salvar_card_grafico(fig: Figure, chart_file: pathlib.Path, dpi: int = 180) -> None:
    # Rótulos de categoria mais longos que a `margem_esquerda` default estouram
    # a borda esquerda do card. Roda aqui, no caminho por onde todo card passa,
    # em vez de depender de cada `gerar_grafico_*` lembrar de chamar: é no-op
    # quando não há yticklabels ou quando eles já cabem na margem.
    if fig.axes:
        ajustar_margem_esquerda_para_rotulos(fig, fig.axes[0])
    # Sem bbox_inches="tight": a moldura já foi posicionada em coordenadas de
    # figura pensando no figsize exato, e um recorte automático cortaria as
    # bordas/cantos arredondados do card.
    plt.savefig(chart_file, dpi=dpi, facecolor="white")
    plt.close(fig)
