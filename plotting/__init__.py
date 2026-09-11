"""Setup compartilhado dos gráficos matplotlib.

Roda uma vez no primeiro import de qualquer ``plotting.*``: registra a fonte
Inter (mesma do relatório HTML) e a torna padrão, para os gráficos casarem com
a tipografia do restante do documento. Sem isso o matplotlib cai no DejaVu Sans.
"""

import logging
import pathlib
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.transforms import blended_transform_factory

logger = logging.getLogger(__name__)

_FONTS_DIR = Path(__file__).resolve().parent.parent / "report" / "src" / "styles" / "fonts"
_ARQUIVOS_INTER = ("Inter-Regular.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf")

# Multiplicador aplicado a todos os tamanhos de fonte dos gráficos (fontsize/
# labelsize). Preserva as proporções entre os textos; ajuste este único número
# para deixar os rótulos/números maiores ou menores de forma uniforme.
ESCALA_FONTE = 1.15


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
        fontweight=600,
        color=_CARD_COR_TITULO,
        zorder=3,
    )

    corpo_esq = margem + margem_esquerda
    corpo_dir = 1 - margem - 0.045
    corpo_topo = 1 - margem - altura_header - 0.03
    corpo_base = margem + 0.06
    ax = fig.add_axes(
        (corpo_esq, corpo_base, corpo_dir - corpo_esq, corpo_topo - corpo_base)
    )
    ax.set_zorder(3)
    return fig, ax


def ajustar_margem_esquerda_para_rotulos(
    fig: Figure, ax: "plt.Axes", pad_polegadas: float = 0.08
) -> None:
    # `margem_esquerda` de `iniciar_card_grafico` é um valor fixo, pensado
    # pro caso comum; rótulos de categoria mais longos que o previsto (ex.:
    # nomes de vacina) estouram essa margem e saem cortados pra fora do card.
    # Mede a largura real já desenhada dos `yticklabels` (e do `ylabel`, se
    # houver) e reconstrói o layout à esquerda do zero: [borda do card] ->
    # [ylabel, se houver] -> [yticklabels] -> [eixo].
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    rotulos_tick = ax.get_yticklabels()
    if not rotulos_tick:
        return

    largura_fig_pol = fig.get_size_inches()[0]
    largura_fig_px = largura_fig_pol * fig.dpi
    pad_px = pad_polegadas * fig.dpi
    borda_card_px = _CARD_MARGEM * largura_fig_px
    largura_ticks_px = max(
        r.get_window_extent(renderer=renderer).width for r in rotulos_tick
    )

    rotulo_eixo = ax.yaxis.get_label()
    tem_ylabel = bool(rotulo_eixo.get_text())
    largura_ylabel_px = 0.0
    if tem_ylabel:
        # A largura de um texto rotacionado 90° é a ALTURA da sua bbox, não a
        # largura (que, rotacionado, vira ~0).
        largura_ylabel_px = rotulo_eixo.get_window_extent(renderer=renderer).height

    bloco_ylabel_px = (largura_ylabel_px + pad_px) if tem_ylabel else 0
    corpo_esq_necessario_px = (
        borda_card_px + pad_px + bloco_ylabel_px + largura_ticks_px
    )

    posicao = ax.get_position()
    corpo_esq_necessario = corpo_esq_necessario_px / largura_fig_px
    if corpo_esq_necessario <= posicao.x0:
        return

    deslocamento = corpo_esq_necessario - posicao.x0
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
        ax.yaxis.set_label_coords(
            (borda_card_px + pad_px + largura_ylabel_px / 2) / largura_fig_px,
            0.5,
            transform=blended_transform_factory(fig.transFigure, ax.transAxes),
        )


def salvar_card_grafico(fig: Figure, chart_file: pathlib.Path) -> None:
    # Sem bbox_inches="tight": a moldura já foi posicionada em coordenadas de
    # figura pensando no figsize exato, e um recorte automático cortaria as
    # bordas/cantos arredondados do card.
    plt.savefig(chart_file, dpi=180, facecolor="white")
    plt.close(fig)
