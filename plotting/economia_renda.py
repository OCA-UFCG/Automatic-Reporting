import pathlib

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter

from plotting.hidraulica import _numero
from utils.queries.economia_renda import _escalar_valor

_COR_LINHA = "#F0883E"

_NOMES_SETORES_VAB = {
    "servicos": "Serviços",
    "industria": "Indústria",
    "adm_publica": "Administração Pública",
    "agropecuaria": "Agropecuária",
}
_CORES_POR_RANKING = ("#F0883E", "#F5C08A", "#F8D9B8", "#FBEADB")
_UNIDADE_ABREVIADA = {"bilhões": "Bi", "milhões": "Mi", "mil": "mil"}


def _dispor_setores_por_valor(
    valores: dict[str, float],
) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
    ordenados = sorted(valores.items(), key=lambda item: item[1], reverse=True)
    return ordenados[:2], ordenados[2:4]


def _atribuir_cores_por_ranking(
    linha1: list[tuple[str, float]], linha2: list[tuple[str, float]]
) -> dict[str, str]:
    ordenados = [chave for chave, _valor in (*linha1, *linha2)]
    return dict(zip(ordenados, _CORES_POR_RANKING))


def _escolher_unidade(valor: float) -> tuple[float, str]:
    _, unidade = _escalar_valor(valor)
    divisor = {"bilhões": 1e9, "milhões": 1e6, "mil": 1e3}.get(unidade, 1)
    return divisor, unidade


def gerar_grafico_pib(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    serie = cidade.get("pib_serie") or []
    pontos = [
        (item["ano"], _numero(item.get("pib_total")))
        for item in serie
        if item.get("ano") is not None and item.get("pib_total") is not None
    ]
    if not pontos:
        raise ValueError("Dados anuais de PIB total não disponíveis.")

    anos = [ano for ano, _ in pontos]
    valores = [valor for _, valor in pontos]
    divisor_eixo, unidade_eixo = _escolher_unidade(max(valores))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_pib_{safe_city}.png"

    fig, ax = plt.subplots(figsize=(10, 4.5))

    ax.plot(
        anos,
        valores,
        linestyle=":",
        marker="o",
        linewidth=2,
        markersize=5,
        color=_COR_LINHA,
        markerfacecolor=_COR_LINHA,
        markeredgecolor=_COR_LINHA,
    )

    for ano, valor in zip(anos, valores):
        divisor_ponto, unidade_ponto = _escolher_unidade(valor)
        sufixo_ponto = f" {unidade_ponto}" if unidade_ponto else ""
        ax.annotate(
            f"R$ {valor / divisor_ponto:.1f}{sufixo_ponto}",
            (ano, valor),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color="#4A4A4A",
        )

    ax.set_title(
        "Evolução anual do PIB Total",
        loc="left",
        fontsize=11,
        fontweight="bold",
    )

    valor_minimo = min(valores)
    valor_maximo = max(valores)
    amplitude = valor_maximo - valor_minimo or valor_maximo or 1.0
    margem = amplitude * 0.15
    ax.set_ylim(valor_minimo - margem, valor_maximo + margem)

    ax.set_xticks(anos)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    ax.grid(axis="y", linestyle=":", alpha=0.4)

    sufixo_eixo = f" {unidade_eixo}" if unidade_eixo else ""
    ax.yaxis.set_major_formatter(
        FuncFormatter(lambda valor, _: f"R$ {valor / divisor_eixo:.0f}{sufixo_eixo}")
    )

    fig.tight_layout()
    fig.savefig(chart_file, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return chart_file.name


def gerar_grafico_fob(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    paises = cidade.get("importacao_paises") or []
    pontos = [
        (nome, _numero(valor))
        for nome, valor in paises
        if nome is not None and valor is not None
    ]
    if not pontos:
        raise ValueError("Dados de países de importação não disponíveis.")

    pontos = sorted(pontos, key=lambda item: item[1], reverse=True)
    nomes = [nome for nome, _valor in pontos]
    valores = [valor for _nome, valor in pontos]

    cores = plt.get_cmap("RdYlBu")(
        [indice / max(len(pontos) - 1, 1) for indice in range(len(pontos))]
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_fob_{safe_city}.png"

    fig, ax = plt.subplots(figsize=(10, 0.5 * len(pontos) + 1.5))

    posicoes = range(len(pontos))
    ax.barh(posicoes, valores, color=cores)
    ax.set_yticks(list(posicoes))
    ax.set_yticklabels(nomes)
    ax.invert_yaxis()

    for posicao, valor in zip(posicoes, valores):
        valor_escalado, unidade = _escalar_valor(valor)
        sufixo = f" {_UNIDADE_ABREVIADA.get(unidade, unidade)}" if unidade else ""
        ax.text(
            valor,
            posicao,
            f" ${valor_escalado:.2f}{sufixo}",
            va="center",
            ha="left",
            fontsize=8,
            color="#3A2A1A",
        )

    ax.set_xlabel("Valor líquido FOB (US$)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda valor, _: f"${valor / 1e9:.1f} Bi"))
    ax.set_xlim(0, max(valores) * 1.2)

    fig.tight_layout()
    fig.savefig(chart_file, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return chart_file.name


def gerar_grafico_vab(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    setores = cidade.get("vab_setores_2021") or {}
    valores = {chave: _numero(setores.get(chave)) for chave in _NOMES_SETORES_VAB}
    if not any(valores.values()):
        raise ValueError("Dados de VAB por setor não disponíveis.")

    total = sum(valores.values())
    linha1, linha2 = _dispor_setores_por_valor(valores)
    linhas = (linha1, linha2)
    cores = _atribuir_cores_por_ranking(linha1, linha2)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_vab_{safe_city}.png"

    fig, ax = plt.subplots(figsize=(10, 5))

    y_topo = 1.0
    for linha in linhas:
        soma_linha = sum(valor for _chave, valor in linha)
        altura_linha = soma_linha / total if total else 0
        x_esquerda = 0.0
        for chave, valor in linha:
            nome = _NOMES_SETORES_VAB[chave]
            largura = (valor / soma_linha) if soma_linha else 0
            ax.add_patch(
                Rectangle(
                    (x_esquerda, y_topo - altura_linha),
                    largura,
                    altura_linha,
                    facecolor=cores[chave],
                    edgecolor="white",
                    linewidth=2,
                )
            )
            valor_escalado, unidade = _escalar_valor(valor)
            sufixo = f" {unidade}" if unidade else ""
            ax.text(
                x_esquerda + 0.015,
                y_topo - 0.04,
                nome,
                ha="left",
                va="top",
                fontsize=9,
                fontweight="bold",
                color="#3A2A1A",
            )
            ax.text(
                x_esquerda + 0.015,
                y_topo - altura_linha + 0.04,
                f"R$ {valor_escalado:.2f}{sufixo}",
                ha="left",
                va="bottom",
                fontsize=9,
                color="#3A2A1A",
            )
            x_esquerda += largura
        y_topo -= altura_linha

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    fig.tight_layout()
    fig.savefig(chart_file, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return chart_file.name
