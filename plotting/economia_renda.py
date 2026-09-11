import pathlib
import textwrap

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter

from plotting import ESCALA_FONTE, iniciar_card_grafico, salvar_card_grafico
from plotting.hidraulica import _numero
from utils.formatting import formatar_numero_ptbr
from utils.queries.economia_renda import _escalar_valor

_COR_LINHA = "#F0883E"

_NOMES_SETORES_VAB = {
    "servicos": "Serviços",
    "industria": "Indústria",
    "adm_publica": "Administração Pública",
    "agropecuaria": "Agropecuária",
}
_CORES_POR_RANKING = ("#F0883E", "#F5C08A", "#F8D9B8", "#FBEADB")
_UNIDADE_ABREVIADA = {"trilhões": "Ti", "bilhões": "Bi", "milhões": "Mi", "mil": "mil"}


def _reservar_espaco_rotulo_x(fig, ax, reserva_polegadas: float = 0.34) -> None:
    # Mesmo ajuste de plotting.saude/demografia: `iniciar_card_grafico`
    # posiciona o corpo do card sem folga abaixo dos rótulos do eixo X — eles
    # ficam colados na borda inferior da moldura. Encolhe o eixo reservando
    # uma faixa fixa, em polegadas, na base do card.
    altura_fig = fig.get_size_inches()[1]
    fracao = reserva_polegadas / altura_fig
    posicao = ax.get_position()
    ax.set_position(
        (posicao.x0, posicao.y0 + fracao, posicao.width, posicao.height - fracao)
    )


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

    fig, ax = iniciar_card_grafico(
        (24, 7),
        "Evolução anual do PIB Total",
        margem_esquerda=0.08,
        tamanho_titulo=18,
    )
    _reservar_espaco_rotulo_x(fig, ax)

    ax.plot(
        anos,
        valores,
        linestyle=":",
        marker="o",
        linewidth=2.5,
        markersize=8,
        color=_COR_LINHA,
        markerfacecolor=_COR_LINHA,
        markeredgecolor=_COR_LINHA,
    )

    valor_minimo = min(valores)
    valor_maximo = max(valores)
    amplitude = valor_maximo - valor_minimo or valor_maximo or 1.0
    # Margem extra no topo (0.28 em vez de 0.15) para as anotações de valor,
    # que ficam acima de cada ponto, não colarem na faixa de título do card.
    margem = amplitude * 0.15
    # Fixa os limites do eixo Y antes de anotar: a posição em pixels de cada
    # rótulo (usada logo abaixo pra detectar sobreposição) depende dos
    # limites vigentes no momento do desenho, e eles têm que ser os finais.
    ax.set_ylim(valor_minimo - margem, valor_maximo + amplitude * 0.28)
    ax.set_xticks(anos)

    for ano, valor in zip(anos, valores):
        divisor_ponto, unidade_ponto = _escolher_unidade(valor)
        # "Mi"/"Bi"/"Ti" em vez do nome por extenso só aqui: é só o rótulo do
        # ponto, mais compacto pra sobrar espaço no eixo X lotado de anos; o
        # eixo Y (abaixo) continua com a unidade por extenso.
        unidade_ponto_abreviada = {
            "milhões": "Mi",
            "bilhões": "Bi",
            "trilhões": "Ti",
        }.get(unidade_ponto, unidade_ponto)
        sufixo_ponto = f" {unidade_ponto_abreviada}" if unidade_ponto_abreviada else ""
        ax.annotate(
            f"R$ {valor / divisor_ponto:.1f}{sufixo_ponto}",
            (ano, valor),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            fontsize=12 * ESCALA_FONTE * 1.15,
            color="#4A4A4A",
        )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    ax.grid(axis="y", linestyle=":", alpha=0.4)

    sufixo_eixo = f" {unidade_eixo}" if unidade_eixo else ""
    ax.yaxis.set_major_formatter(
        FuncFormatter(lambda valor, _: f"R$ {valor / divisor_eixo:.0f}{sufixo_eixo}")
    )
    ax.tick_params(axis="both", labelsize=13 * ESCALA_FONTE)

    salvar_card_grafico(fig, chart_file, dpi=270)
    return chart_file.name


def _gerar_grafico_ranking_paises(
    paises: list[tuple[str, object]],
    chart_file: pathlib.Path,
    mensagem_erro: str,
    titulo: str,
) -> str:
    pontos = [
        (nome, _numero(valor))
        for nome, valor in paises
        if nome is not None and valor is not None
    ]
    if not pontos:
        raise ValueError(mensagem_erro)

    pontos = sorted(pontos, key=lambda item: item[1], reverse=True)
    nomes = [nome for nome, _valor in pontos]
    valores = [valor for _nome, valor in pontos]

    cores = plt.get_cmap("Spectral")(
        [indice / max(len(pontos) - 1, 1) for indice in range(len(pontos))]
    )

    chart_file.parent.mkdir(parents=True, exist_ok=True)

    altura = max(0.5 * len(pontos) + 2.2, 3.4)
    fig, ax = iniciar_card_grafico((10, altura), titulo)
    # A margem inferior do card é uma FRAÇÃO da altura da figura, mas o
    # espaço exigido pelos ticks + label do eixo x é fixo (fonte de tamanho
    # constante); com poucos países essa fração não bastava e o rótulo saía
    # cortado na moldura. Reserva uma faixa fixa, em polegadas, na base.
    posicao = ax.get_position()
    reserva = 0.55 / altura
    ax.set_position(
        (posicao.x0, posicao.y0 + reserva, posicao.width, posicao.height - reserva)
    )

    posicoes = range(len(pontos))
    ax.barh(posicoes, valores, color=cores, zorder=3)
    ax.set_yticks(list(posicoes))
    ax.set_yticklabels(nomes, fontsize=13)
    ax.invert_yaxis()

    for posicao, valor in zip(posicoes, valores):
        valor_escalado, unidade = _escalar_valor(valor)
        sufixo = f" {_UNIDADE_ABREVIADA.get(unidade, unidade)}" if unidade else ""
        ax.text(
            valor,
            posicao,
            f" ${formatar_numero_ptbr(valor_escalado, decimais=2)}{sufixo}",
            va="center",
            ha="left",
            fontsize=13,
            color="#3A2A1A",
        )

    ax.set_xlabel("Valor líquido FOB (US$)", fontsize=13)
    ax.tick_params(axis="x", labelsize=13)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.grid(axis="x", linestyle=":", color="#CCCCCC", zorder=0)
    ax.set_axisbelow(True)
    divisor_eixo, unidade_eixo = _escolher_unidade(max(valores))
    ax.xaxis.set_major_formatter(
        FuncFormatter(
            lambda valor, _: f"${formatar_numero_ptbr(valor / divisor_eixo, decimais=1)}"
        )
    )
    ax.set_xlim(0, max(valores) * 1.2)

    if unidade_eixo:
        # Unidade uma vez só, à esquerda, na altura dos ticks — em vez de
        # repetir "Mi" em cada tick do eixo X (redundante e mais apertado).
        nome_unidade = {
            "trilhões": "Trilhões",
            "bilhões": "Bilhões",
            "milhões": "Milhões",
            "mil": "Mil",
        }.get(unidade_eixo, unidade_eixo.capitalize())
        abreviacao_unidade = _UNIDADE_ABREVIADA.get(unidade_eixo, unidade_eixo)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        bbox_tick = ax.get_xticklabels()[0].get_window_extent(renderer=renderer)
        _, y_altura_tick = fig.transFigure.inverted().transform(
            (0, (bbox_tick.y0 + bbox_tick.y1) / 2)
        )
        fig.text(
            0.03,
            y_altura_tick,
            f"{nome_unidade} ({abreviacao_unidade})",
            transform=fig.transFigure,
            ha="left",
            va="center",
            fontsize=13,
            color="#4A4A4A",
        )

    salvar_card_grafico(fig, chart_file)
    return chart_file.name


def gerar_grafico_fob(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    return _gerar_grafico_ranking_paises(
        cidade.get("importacao_paises") or [],
        OUTPUT_DIR / f"grafico_fob_{safe_city}.png",
        "Dados de países de importação não disponíveis.",
        "Destinos das importações ordenados pelo valor líquido FOB",
    )


def gerar_grafico_exportacao(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    return _gerar_grafico_ranking_paises(
        cidade.get("exportacao_paises") or [],
        OUTPUT_DIR / f"grafico_exportacao_{safe_city}.png",
        "Dados de países de exportação não disponíveis.",
        "Destinos das exportações ordenados pelo valor líquido FOB",
    )


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

    # margem_esquerda pequena: o treemap não tem rótulos de eixo Y, então a
    # folga padrão (pensada pra rótulos de categoria) só deixaria uma faixa
    # em branco à esquerda do card.
    fig, ax = iniciar_card_grafico(
        (10, 5), "Valor Adicionado Bruto (VAB) por setor", margem_esquerda=0.03
    )

    _MARGEM_TEXTO = 0.015
    textos_por_largura = []

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
            texto_nome = ax.text(
                x_esquerda + _MARGEM_TEXTO,
                y_topo - 0.04,
                nome,
                ha="left",
                va="top",
                fontsize=11.9,
                fontweight="bold",
                color="#3A2A1A",
            )
            texto_valor = ax.text(
                x_esquerda + _MARGEM_TEXTO,
                y_topo - altura_linha + 0.04,
                f"R$ {valor_escalado:.2f}{sufixo}",
                ha="left",
                va="bottom",
                fontsize=11.9,
                color="#3A2A1A",
            )
            largura_disponivel = largura - 2 * _MARGEM_TEXTO
            textos_por_largura.append((texto_nome, largura_disponivel))
            textos_por_largura.append((texto_valor, largura_disponivel))
            x_esquerda += largura
        y_topo -= altura_linha

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    _FONTE_MINIMA = 11.9
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    origem_px = ax.transData.transform((0, 0))[0]
    for texto_obj, largura_disponivel in textos_por_largura:
        if largura_disponivel <= 0:
            continue
        largura_disponivel_px = (
            ax.transData.transform((largura_disponivel, 0))[0] - origem_px
        )
        largura_texto_px = texto_obj.get_window_extent(renderer=renderer).width
        if largura_texto_px <= largura_disponivel_px:
            continue

        fonte_ajustada = max(
            texto_obj.get_fontsize() * largura_disponivel_px / largura_texto_px,
            _FONTE_MINIMA,
        )
        texto_obj.set_fontsize(fonte_ajustada)

        fig.canvas.draw()
        largura_texto_px = texto_obj.get_window_extent(renderer=renderer).width
        texto = texto_obj.get_text()
        if largura_texto_px > largura_disponivel_px and " " in texto:
            largura_linha = 1
            linhas_quebradas = textwrap.wrap(texto, width=largura_linha)
            while len(linhas_quebradas) > 2 and largura_linha < len(texto):
                largura_linha += 1
                linhas_quebradas = textwrap.wrap(texto, width=largura_linha)
            texto_obj.set_text("\n".join(linhas_quebradas))

    salvar_card_grafico(fig, chart_file)
    return chart_file.name


def gerar_grafico_balanca(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    serie = cidade.get("balanca_mensal") or []
    pontos = [
        (mes, _numero(valor))
        for mes, valor in serie
        if mes is not None and valor is not None
    ]
    if not pontos:
        raise ValueError("Dados mensais de balança comercial não disponíveis.")

    meses = [f"{mes}." for mes, _valor in pontos]
    valores = [valor for _mes, valor in pontos]
    divisor_eixo, unidade_eixo = _escolher_unidade(max(abs(valor) for valor in valores))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_balanca_{safe_city}.png"

    fig, ax = iniciar_card_grafico((10, 4.5), "Visão mensal da balança comercial")
    _reservar_espaco_rotulo_x(fig, ax)

    posicoes = range(len(pontos))
    ax.bar(posicoes, valores, color=_COR_LINHA, zorder=3)
    ax.set_xticks(list(posicoes))
    ax.set_xticklabels(meses, fontsize=13)
    ax.axhline(0, color="#4A4A4A", linewidth=1, zorder=3)

    for posicao, valor in zip(posicoes, valores):
        valor_escalado, unidade = _escalar_valor(abs(valor))
        sufixo = f" {unidade}" if unidade else ""
        sinal = "-" if valor < 0 else ""
        ax.annotate(
            f"{sinal}{formatar_numero_ptbr(valor_escalado, decimais=2)}{sufixo}",
            (posicao, valor),
            xytext=(0, 6 if valor >= 0 else -14),
            textcoords="offset points",
            ha="center",
            fontsize=13,
            color="#3A2A1A",
        )

    ax.set_ylabel("Saldo da balança comercial (US$)", fontsize=13)
    ax.tick_params(axis="y", labelsize=13)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.grid(axis="y", linestyle=":", color="#CCCCCC", zorder=0)
    ax.set_axisbelow(True)

    # Margem extra acima/abaixo das barras para as anotações de valor (que
    # ficam fora delas) não colarem na faixa de título do card nem no rodapé.
    valor_minimo = min(0, min(valores))
    valor_maximo = max(0, max(valores))
    amplitude = valor_maximo - valor_minimo or 1.0
    ax.set_ylim(valor_minimo - amplitude * 0.12, valor_maximo + amplitude * 0.15)

    sufixo_eixo = f" {unidade_eixo}" if unidade_eixo else ""
    ax.yaxis.set_major_formatter(
        FuncFormatter(
            lambda valor, _: f"{formatar_numero_ptbr(valor / divisor_eixo, decimais=1)}{sufixo_eixo}"
        )
    )

    salvar_card_grafico(fig, chart_file)
    return chart_file.name
