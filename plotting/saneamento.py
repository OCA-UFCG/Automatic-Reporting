import math
import pathlib

from matplotlib.ticker import FuncFormatter, MaxNLocator

from plotting import ESCALA_FONTE, iniciar_card_grafico, salvar_card_grafico

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
        return f"{round(total / 1000)}K"
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

    fig, ax = iniciar_card_grafico(
        (8, 4.6), "Domicílios por tipo de esgotamento sanitário"
    )
    # A legenda fica à direita da rosca (fora do eixo, na horizontal) — encolhe
    # a largura do `ax` pra sobrar uma faixa à direita, dentro do card, onde
    # ela cabe inteira sem vazar da moldura nem se sobrepor à rosca.
    posicao = ax.get_position()
    largura_legenda = posicao.width * 0.44
    ax.set_position(
        (posicao.x0, posicao.y0, posicao.width - largura_legenda, posicao.height)
    )

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
        bbox_to_anchor=(1.06, 0.5),
        frameon=False,
        fontsize=8.5*ESCALA_FONTE,
        handlelength=1.0,
        labelspacing=0.7,
    )
    ax.set_aspect("equal")

    salvar_card_grafico(fig, chart_file)
    return chart_file.name


def _grafico_evolucao_percentual(
    pontos: list[tuple[str, float]], titulo: str, chart_file: pathlib.Path
) -> None:
    """Card de barras com um percentual por ano (0–100%), rotulado no topo.

    Compartilhado pelas Figuras 2 e 4 do saneamento — mesma forma, só muda o
    título e a série. Os valores das colunas `esgoto_rede_*`/`coleta_*` da view
    já são percentuais de domicílios.
    """
    anos = [ano for ano, _ in pontos]
    valores = [valor for _, valor in pontos]
    x = list(range(len(anos)))

    fig, ax = iniciar_card_grafico((8, 4.0), titulo)

    barras = ax.bar(x, valores, width=0.5, color="#5B8DEF", zorder=3)

    # Folga no topo pra caber o rótulo da barra mais alta; piso de 10% evita
    # que uma série toda baixa vire barras minúsculas coladas no eixo.
    limite = max(max(valores, default=0) * 1.25, 10)
    ax.set_ylim(0, limite)
    for barra, valor in zip(barras, valores):
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

    ax.set_xticks(x)
    ax.set_xticklabels(anos, fontsize=9 * ESCALA_FONTE)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
    ax.grid(axis="y", linestyle="--", linewidth=0.5, color="#D9D9D9", alpha=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", length=0, labelsize=9 * ESCALA_FONTE, colors="#4A4A4A")
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color("#4A4A4A")

    salvar_card_grafico(fig, chart_file)


def gerar_grafico_evolucao_rede_geral_esgoto(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    """Figura 2 — evolução do % de domicílios conectados à rede geral/pluvial."""
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
        raise ValueError("Dados de evolução da rede geral de esgoto não disponíveis.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_evolucao_rede_geral_esgoto_{safe_city}.png"
    _grafico_evolucao_percentual(
        pontos, "Domicílios conectados à rede geral de esgoto ou pluvial", chart_file
    )
    return chart_file.name


def gerar_grafico_evolucao_coleta_lixo(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    """Figura 4 — evolução do % de domicílios com coleta de lixo."""
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
    _grafico_evolucao_percentual(pontos, "Domicílios com coleta de lixo", chart_file)
    return chart_file.name
