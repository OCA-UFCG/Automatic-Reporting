import pathlib
import textwrap

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter

from plotting import (
    ESCALA_FONTE,
    iniciar_card_grafico,
    reusar_grafico,
    salvar_card_grafico,
)
from plotting.hidraulica import _numero
from utils.formatting import formatar_numero_ptbr
from utils.queries.base import escalar_valor as _escalar_valor
from utils.queries.base import escalar_valor_por_extenso

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


def _adicionar_legenda_externa(fig, ax, celulas: list[dict], cores: dict[str, str]) -> None:
    # Reserva uma faixa na base do card (encolhendo o eixo por cima, como em
    # `_reservar_espaco_rotulo_x`) e escreve ali, alinhado à direita, um
    # quadradinho com a cor da célula + "Nome — R$ valor" de cada setor que
    # não coube dentro do próprio retângulo.
    _reservar_espaco_rotulo_x(fig, ax, reserva_polegadas=0.42)
    posicao = ax.get_position()
    altura_fig = fig.get_size_inches()[1]
    y_legenda = posicao.y0 - 0.21 / altura_fig
    x_direita = posicao.x1
    largura_fig_px = fig.get_size_inches()[0] * fig.dpi
    renderer = fig.canvas.get_renderer()
    for celula in reversed(celulas):
        texto = fig.text(
            x_direita,
            y_legenda,
            f"{celula['nome']} — {celula['texto_valor_str']}",
            ha="right",
            va="center",
            fontsize=10 * ESCALA_FONTE,
            color="#3A2A1A",
        )
        largura_texto = texto.get_window_extent(renderer=renderer).width / largura_fig_px
        lado_quadrado = 0.14 / fig.get_size_inches()[0]
        x_quadrado = x_direita - largura_texto - 0.06 / fig.get_size_inches()[0] - lado_quadrado
        fig.patches.append(
            Rectangle(
                (x_quadrado, y_legenda - 0.07 / altura_fig),
                lado_quadrado,
                0.14 / altura_fig,
                transform=fig.transFigure,
                figure=fig,
                facecolor=cores[celula["chave"]],
                edgecolor="#C9B8A6",
                linewidth=0.6,
            )
        )
        x_direita = x_quadrado - 0.3 / fig.get_size_inches()[0]


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
    reuso = reusar_grafico(chart_file)
    if reuso is not None:
        return reuso

    fig, ax = iniciar_card_grafico(
        (16, 6.5),
        "PIB total",
        margem_esquerda=0.08,
        tamanho_titulo=24,
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
    ax.set_ylabel("Produto interno", fontsize=20 * ESCALA_FONTE)
    ax.tick_params(axis="both", labelsize=20 * ESCALA_FONTE)

    salvar_card_grafico(fig, chart_file, dpi=270)
    return chart_file.name


def _gerar_grafico_ranking_paises(
    paises: list[tuple[str, object]],
    chart_file: pathlib.Path,
    mensagem_erro: str,
    titulo: str,
) -> str:
    # Guard único aqui (não em cada `gerar_grafico_*` chamador): `gerar_grafico_fob`
    # e `gerar_grafico_exportacao` só montam o `chart_file` e delegam pra este
    # helper compartilhado, que é onde a figura de fato é desenhada — colocar o
    # guard em cada chamador duplicaria a checagem sem cobrir nada a mais.
    reuso = reusar_grafico(chart_file)
    if reuso is not None:
        return reuso

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
    ax.set_yticklabels(nomes, fontsize=13 * ESCALA_FONTE)
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
            fontsize=13 * ESCALA_FONTE,
            color="#3A2A1A",
        )

    ax.set_xlabel("Valor líquido FOB (US$)", fontsize=13 * ESCALA_FONTE)
    ax.tick_params(axis="x", labelsize=13 * ESCALA_FONTE)
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
            fontsize=13 * ESCALA_FONTE,
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
        "Origem(ns) das importações pelo valor líquido FOB",
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
    reuso = reusar_grafico(chart_file)
    if reuso is not None:
        return reuso

    # margem_esquerda pequena: o treemap não tem rótulos de eixo Y, então a
    # folga padrão (pensada pra rótulos de categoria) só deixaria uma faixa
    # em branco à esquerda do card.
    fig, ax = iniciar_card_grafico(
        (10, 5), "Valor Adicionado Bruto (VAB) por setor", margem_esquerda=0.03
    )

    _MARGEM_TEXTO = 0.015
    _MARGEM_VERTICAL = 0.04
    textos_por_largura = []
    celulas = []

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
            # Rótulo por extenso, como no texto: "R$ 1,76 bilhão", não "bilhões".
            valor_escalado, unidade = escalar_valor_por_extenso(valor)
            sufixo = f" {unidade}" if unidade else ""
            texto_valor_str = f"R$ {formatar_numero_ptbr(valor_escalado, decimais=2)}{sufixo}"
            texto_nome = ax.text(
                x_esquerda + _MARGEM_TEXTO,
                y_topo - _MARGEM_VERTICAL,
                nome,
                ha="left",
                va="top",
                fontsize=11.9 * ESCALA_FONTE,
                fontweight="bold",
                color="#3A2A1A",
                clip_on=True,
            )
            texto_valor = ax.text(
                x_esquerda + _MARGEM_TEXTO,
                y_topo - altura_linha + _MARGEM_VERTICAL,
                texto_valor_str,
                ha="left",
                va="bottom",
                fontsize=11.9 * ESCALA_FONTE,
                color="#3A2A1A",
                clip_on=True,
            )
            largura_disponivel = largura - 2 * _MARGEM_TEXTO
            textos_por_largura.append((texto_nome, largura_disponivel))
            textos_por_largura.append((texto_valor, largura_disponivel))
            celulas.append(
                {
                    "chave": chave,
                    "texto_nome": texto_nome,
                    "texto_valor": texto_valor,
                    "texto_valor_str": texto_valor_str,
                    "nome": nome,
                    "x_texto": x_esquerda + _MARGEM_TEXTO,
                    "y_centro": y_topo - altura_linha / 2,
                    "altura_linha": altura_linha,
                    "largura_disponivel": largura_disponivel,
                }
            )
            x_esquerda += largura
        y_topo -= altura_linha

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    _FONTE_MINIMA = 8 * ESCALA_FONTE
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    origem_px = ax.transData.transform((0, 0))[0]

    def _encolher_para_largura(texto_obj, largura_disponivel_px: float) -> None:
        largura_texto_px = texto_obj.get_window_extent(renderer=renderer).width
        if largura_texto_px <= largura_disponivel_px:
            return

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

    # Setor com fatia muito pequena (ex.: Agropecuária em Rosário do Catete/SE,
    # ~1% do VAB) vira uma célula estreita onde nem o nome cabe na fonte
    # mínima — o texto saía cortado na borda. Aumentar o figsize não resolve:
    # o PNG entra no relatório com largura fixa, então a célula continua com a
    # mesma fração da largura. Nesses casos o rótulo sai da célula e vai pra
    # uma legenda abaixo do treemap, identificada pela cor.
    celulas_externas = []
    for celula in celulas:
        if celula["largura_disponivel"] <= 0:
            celulas_externas.append(celula)
            continue
        largura_disponivel_px = (
            ax.transData.transform((celula["largura_disponivel"], 0))[0] - origem_px
        )
        texto_nome = celula["texto_nome"]
        largura_nome_minima_px = (
            texto_nome.get_window_extent(renderer=renderer).width
            * _FONTE_MINIMA
            / texto_nome.get_fontsize()
        )
        # Mesmo raciocínio na vertical: linha do treemap tão baixa que nem
        # uma linha de texto na fonte mínima cabe (o texto fundido abaixo
        # vazaria pra fora da faixa, por cima da borda do card).
        altura_linha_px = abs(
            ax.transData.transform((0, celula["altura_linha"]))[1]
            - ax.transData.transform((0, 0))[1]
        )
        altura_nome_minima_px = (
            texto_nome.get_window_extent(renderer=renderer).height
            * _FONTE_MINIMA
            / texto_nome.get_fontsize()
        )
        if (
            largura_nome_minima_px > largura_disponivel_px
            or altura_nome_minima_px > altura_linha_px
        ):
            celulas_externas.append(celula)

    ids_externos = {id(celula) for celula in celulas_externas}
    for celula in celulas_externas:
        celula["texto_nome"].remove()
        celula["texto_valor"].remove()
    celulas = [celula for celula in celulas if id(celula) not in ids_externos]
    textos_externos = {
        id(texto)
        for celula in celulas_externas
        for texto in (celula["texto_nome"], celula["texto_valor"])
    }
    textos_por_largura = [
        (texto, largura)
        for texto, largura in textos_por_largura
        if id(texto) not in textos_externos
    ]

    if celulas_externas:
        _adicionar_legenda_externa(fig, ax, celulas_externas, cores)
        fig.canvas.draw()
        origem_px = ax.transData.transform((0, 0))[0]

    for texto_obj, largura_disponivel in textos_por_largura:
        if largura_disponivel <= 0:
            continue
        largura_disponivel_px = (
            ax.transData.transform((largura_disponivel, 0))[0] - origem_px
        )
        _encolher_para_largura(texto_obj, largura_disponivel_px)

    # Nome (va="top") e valor (va="bottom") são duas linhas empilhadas dentro
    # da faixa da célula; numa linha do treemap curta (setores pequenos, ver
    # PR de sobreposição de texto), a faixa fica menor que a altura somada
    # dos dois textos e eles colidem visualmente. Funde em um texto só,
    # centralizado, só nesse caso — as células com espaço de sobra continuam
    # com nome e valor em linhas separadas.
    fig.canvas.draw()
    origem_y_px = ax.transData.transform((0, 0))[1]
    for celula in celulas:
        # O texto do nome (va="top") só começa a desenhar _MARGEM_VERTICAL
        # abaixo do topo da faixa, e o do valor (va="bottom") só até
        # _MARGEM_VERTICAL antes da base; a folga real entre os dois é a
        # faixa menos essas duas margens, não a faixa inteira.
        altura_util = max(celula["altura_linha"] - 2 * _MARGEM_VERTICAL, 0)
        altura_disponivel_px = abs(
            ax.transData.transform((0, altura_util))[1] - origem_y_px
        )
        altura_texto_px = (
            celula["texto_nome"].get_window_extent(renderer=renderer).height
            + celula["texto_valor"].get_window_extent(renderer=renderer).height
        )
        if altura_texto_px <= altura_disponivel_px:
            continue

        celula["texto_nome"].remove()
        celula["texto_valor"].remove()
        texto_fundido = ax.text(
            celula["x_texto"],
            celula["y_centro"],
            f"{celula['nome']} — {celula['texto_valor_str']}",
            ha="left",
            va="center",
            fontsize=11.9 * ESCALA_FONTE,
            fontweight="bold",
            color="#3A2A1A",
            clip_on=True,
        )
        largura_disponivel_px = (
            ax.transData.transform((celula["largura_disponivel"], 0))[0] - origem_px
        )
        # 85% da faixa: folga pro texto não encostar nas bordas da célula.
        altura_linha_px = 0.85 * abs(
            ax.transData.transform((0, celula["altura_linha"]))[1] - origem_y_px
        )
        fig.canvas.draw()
        altura_fundido_px = texto_fundido.get_window_extent(renderer=renderer).height
        if altura_fundido_px > altura_linha_px:
            texto_fundido.set_fontsize(
                max(
                    texto_fundido.get_fontsize() * altura_linha_px / altura_fundido_px,
                    _FONTE_MINIMA,
                )
            )
            fig.canvas.draw()
        _encolher_para_largura(texto_fundido, largura_disponivel_px)

    salvar_card_grafico(fig, chart_file)
    return chart_file.name


def gerar_grafico_balanca(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    fob_exportado = _numero(cidade.get("fob_exportado_ultimo"))
    fob_importado = _numero(cidade.get("fob_importado_ultimo"))
    if not fob_exportado or not fob_importado:
        raise ValueError(
            "Gráfico de balança comercial exige fob_exportado_ultimo e "
            "fob_importado_ultimo diferentes de zero."
        )

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
    reuso = reusar_grafico(chart_file)
    if reuso is not None:
        return reuso

    fig, ax = iniciar_card_grafico((10, 4.5), "Visão mensal da balança comercial")
    _reservar_espaco_rotulo_x(fig, ax)

    posicoes = range(len(pontos))
    ax.bar(posicoes, valores, color=_COR_LINHA, zorder=3)
    ax.set_xticks(list(posicoes))
    ax.set_xticklabels(meses, fontsize=13 * ESCALA_FONTE)
    ax.axhline(0, color="#4A4A4A", linewidth=1, zorder=3)

    for posicao, valor in zip(posicoes, valores):
        valor_escalado, unidade = _escalar_valor(abs(valor))
        # "Mi"/"Bi" em vez do nome por extenso: com 8 meses no eixo X os
        # rótulos ficam lado a lado e o nome por extenso ("milhões") colide
        # com a barra vizinha.
        sufixo = f" {_UNIDADE_ABREVIADA.get(unidade, unidade)}" if unidade else ""
        sinal = "-" if valor < 0 else ""
        ax.annotate(
            f"{sinal}{formatar_numero_ptbr(valor_escalado, decimais=2)}{sufixo}",
            (posicao, valor),
            xytext=(0, 6 if valor >= 0 else -14),
            textcoords="offset points",
            ha="center",
            fontsize=13 * ESCALA_FONTE,
            color="#3A2A1A",
        )

    ax.set_ylabel("Saldo da balança comercial (US$)", fontsize=13 * ESCALA_FONTE)
    ax.tick_params(axis="y", labelsize=13 * ESCALA_FONTE)
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
