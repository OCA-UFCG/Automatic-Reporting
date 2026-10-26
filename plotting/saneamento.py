import math
import pathlib

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


# Largura máxima, em caracteres, de uma linha de rótulo na legenda. Acima
# disso o texto fica mais largo que a faixa reservada à legenda e vaza a
# borda do card — o que já aconteceu com "Não tinham banheiro e/ou
# sanitário", o mais longo de `_CATEGORIAS`. O corte é por comprimento (e não
# por um texto fixo) para continuar valendo se um rótulo do Doc for
# renomeado ou se uma categoria nova entrar em `_CATEGORIAS`.
_MAX_CARACTERES_ROTULO_LEGENDA = 30


def _quebrar_rotulo_longo(rotulo: str) -> str:
    """Quebra o rótulo em duas linhas no último espaço que ainda cabe na
    largura da legenda. Rótulos curtos voltam inalterados."""
    if len(rotulo) <= _MAX_CARACTERES_ROTULO_LEGENDA:
        return rotulo
    corte = rotulo.rfind(" ", 0, _MAX_CARACTERES_ROTULO_LEGENDA + 1)
    if corte <= 0:
        return rotulo
    return f"{rotulo[:corte]}\n{rotulo[corte + 1:]}"


# Rótulos de percentual: todos ficam FORA da rosca, em duas colunas (direita
# e esquerda), ligados à sua fatia por uma linha-guia. As fatias são
# desenhadas na proporção REAL — a versão anterior (46b4f5e) dava um piso de
# 16° a cada fatia para os rótulos caberem, e isso fazia 0,02% e 0,22%
# parecerem iguais e a fatia de 67% parecer metade do círculo (revisão de
# Segurança Hídrica). Quem abre espaço para os rótulos agora é o
# posicionamento deles, não o desenho.
#
# Distância (em frações do raio da rosca) do texto ao centro, na horizontal.
_X_COLUNA_ROTULO = 1.30
# Raio onde cada rótulo "gostaria" de ficar, alinhado ao meio da sua fatia.
_RAIO_ROTULO = 1.18
# Espaço vertical mínimo entre dois rótulos da mesma coluna — a altura de uma
# linha de texto em `FONTE_ROTULO_VALOR`, com folga, em unidades do raio.
_ESPACO_ENTRE_ROTULOS = 0.19
# Faixa vertical onde os rótulos podem ser empilhados sem sair do eixo.
_Y_MAXIMO_ROTULO = 1.45


def _angulos_dos_meios(valores: list[float]) -> dict[int, float]:
    """Ângulo (graus, convenção matemática) do meio de cada fatia com valor
    > 0, na mesma geometria de `ax.pie(startangle=90, counterclock=False)`:
    começa no topo e anda no sentido horário."""
    total = sum(valores)
    if total <= 0:
        return {}

    meios: dict[int, float] = {}
    acumulado = 0.0
    for indice, valor in enumerate(valores):
        if valor > 0:
            meios[indice] = 90.0 - 360.0 * (acumulado + valor / 2) / total
        acumulado += valor

    return meios


def _blocos_colidem(cima: list[float], baixo: list[float]) -> bool:
    base_de_cima = cima[0] - _ESPACO_ENTRE_ROTULOS * (cima[1] - 1) / 2
    topo_de_baixo = baixo[0] + _ESPACO_ENTRE_ROTULOS * (baixo[1] - 1) / 2

    return base_de_cima - topo_de_baixo < _ESPACO_ENTRE_ROTULOS


def _espalhar_coluna(ideais: list[float]) -> list[float]:
    """Alturas finais de uma coluna de rótulos, dadas as alturas ideais em
    ordem decrescente. Rótulos que se sobrepõem viram um bloco centrado na
    média das suas alturas ideais (em vez de só empurrar para baixo), e o
    bloco é contido em ±`_Y_MAXIMO_ROTULO`. Mantém a ordem de entrada."""
    # Cada bloco: [média das alturas ideais, quantidade de rótulos].
    blocos: list[list[float]] = []
    for ideal in ideais:
        blocos.append([ideal, 1])
        while len(blocos) > 1 and _blocos_colidem(blocos[-2], blocos[-1]):
            baixo = blocos.pop()
            cima = blocos[-1]
            quantidade = cima[1] + baixo[1]
            cima[0] = (cima[0] * cima[1] + baixo[0] * baixo[1]) / quantidade
            cima[1] = quantidade

    alturas: list[float] = []
    for centro, quantidade in blocos:
        meia_altura = _ESPACO_ENTRE_ROTULOS * (quantidade - 1) / 2
        centro = min(centro, _Y_MAXIMO_ROTULO - meia_altura)
        centro = max(centro, -_Y_MAXIMO_ROTULO + meia_altura)
        topo = centro + meia_altura
        alturas.extend(topo - _ESPACO_ENTRE_ROTULOS * i for i in range(int(quantidade)))

    return alturas


def _posicoes_dos_rotulos(valores: list[float]) -> dict[int, tuple[float, float, float]]:
    """(ângulo do meio da fatia, x do texto, y do texto) de cada fatia com
    valor > 0. Fatias do lado direito vão para a coluna da direita e as do
    esquerdo para a da esquerda; dentro de cada coluna os rótulos são
    espalhados na vertical sem se sobrepor e na mesma ordem das fatias —
    por isso as linhas-guia não se cruzam."""
    meios = _angulos_dos_meios(valores)
    posicoes: dict[int, tuple[float, float, float]] = {}

    for lado in (1, -1):
        indices = [
            indice for indice, angulo in meios.items()
            if (math.cos(math.radians(angulo)) >= 0) == (lado == 1)
        ]
        indices.sort(key=lambda indice: -math.sin(math.radians(meios[indice])))
        ideais = [_RAIO_ROTULO * math.sin(math.radians(meios[i])) for i in indices]
        for indice, y in zip(indices, _espalhar_coluna(ideais)):
            posicoes[indice] = (meios[indice], lado * _X_COLUNA_ROTULO, y)

    return posicoes


def _formatar_total(total: float) -> str:
    # "mil" por extenso, e não o "K": a unidade aparece no miolo da rosca,
    # lida por leitores não técnicos do relatório.
    if total >= 10000:
        return f"{round(total / 1000)} mil"
    return f"{total:,.0f}".replace(",", ".")


# Raio do buraco da rosca, em fração do raio externo — mesmo valor de
# `wedgeprops={"width": 0.42}` na chamada de `ax.pie` (a "largura" da fatia é
# medida a partir da borda externa, então o buraco é o raio restante).
_RAIO_BURACO_ROSCA = 1 - 0.42
# Fonte mínima abaixo da qual o total short-circuita legibilidade em vez de
# continuar encolhendo para caber (mesmo piso usado no treemap de VAB, em
# plotting/economia_renda.py).
_FONTE_TOTAL_MINIMA = 14.0
# Encolhe até 85% da largura real do buraco: sem essa folga o texto encosta
# na borda interna da rosca mesmo "cabendo" na medição exata.
_FRACAO_LARGURA_UTIL_BURACO = 0.85


def _fonte_total_ajustada_ao_buraco(fig, ax, texto: str, fontsize_max: float) -> float:
    """Maior fonte, até `fontsize_max`, que faz `texto` caber no buraco da
    rosca. Sem isso, totais que formatam para um texto longo (ex.: "547
    mil") vazam a borda interna — `fontsize_max` fixo só cabe nos totais
    curtos usados nos testes ("1.860")."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    largura_disponivel_px = _FRACAO_LARGURA_UTIL_BURACO * (
        ax.transData.transform((_RAIO_BURACO_ROSCA, 0))[0]
        - ax.transData.transform((-_RAIO_BURACO_ROSCA, 0))[0]
    )
    probe = ax.text(0, 0, texto, fontsize=fontsize_max, fontweight="bold", alpha=0)
    fig.canvas.draw()
    largura_texto_px = probe.get_window_extent(renderer=renderer).width
    probe.remove()
    if largura_texto_px <= largura_disponivel_px or largura_texto_px == 0:
        return fontsize_max
    return max(
        fontsize_max * largura_disponivel_px / largura_texto_px,
        _FONTE_TOTAL_MINIMA,
    )


# Meia-largura do eixo da rosca, em unidades do raio: cabe a coluna de
# rótulos (`_X_COLUNA_ROTULO` + o texto) e a pilha até `_Y_MAXIMO_ROTULO`.
_LIMITE_EIXO_ROSCA = 1.85


def _desenhar_rotulo_com_guia(ax, angulo: float, x: float, y: float, percentual: float) -> None:
    """Escreve o percentual em (x, y) e o liga à borda externa da fatia por
    uma linha-guia com cotovelo: sai radialmente da fatia e segue até o texto."""
    rad = math.radians(angulo)
    borda = (math.cos(rad), math.sin(rad))
    cotovelo = (1.08 * borda[0], 1.08 * borda[1])
    lado = 1 if x > 0 else -1
    ponta = (x - lado * 0.04, y)
    ax.plot(
        [borda[0], cotovelo[0], ponta[0]],
        [borda[1], cotovelo[1], ponta[1]],
        color="#9A9A9A",
        linewidth=0.8,
        solid_capstyle="round",
    )
    ax.text(
        x, y, _formatar_percentual(percentual),
        ha="left" if lado == 1 else "right",
        va="center",
        fontsize=FONTE_ROTULO_VALOR * ESCALA_FONTE,
        color="#4A4A4A",
    )


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
    reuso = reusar_grafico(chart_file)
    if reuso is not None:
        return reuso

    rotulos = [rotulo for _, rotulo, _ in _CATEGORIAS]
    cores = [cor for _, _, cor in _CATEGORIAS]
    rotulos_legenda = [_quebrar_rotulo_longo(rotulo) for rotulo in rotulos]

    fig, ax = iniciar_card_grafico(
        (10, 5.4),
        "Domicílios por tipo de esgotamento sanitário",
        # A rosca não tem eixo Y rotulado, então a margem esquerda default
        # (reservada pra esses rótulos) só empurraria o desenho pra direita.
        margem_esquerda=0.05,
    )
    # A legenda fica à direita da rosca, fora do eixo. Com a fonte 50% maior,
    # a faixa que ela precisa passou a ser maior que a própria rosca: o `ax`
    # cede 56% da largura (antes 44%), senão o rótulo mais longo vaza o card.
    posicao = ax.get_position()
    largura_legenda = posicao.width * 0.42
    ax.set_position(
        (posicao.x0, posicao.y0, posicao.width - largura_legenda, posicao.height)
    )

    # As fatias são desenhadas na proporção real (ver `_posicoes_dos_rotulos`);
    # os percentuais são escritos à parte, fora do anel, com linha-guia.
    percentuais_reais = [100.0 * valor / total for valor in valores]
    wedges, _textos = ax.pie(
        valores,
        colors=cores,
        startangle=90,
        counterclock=False,
        wedgeprops={"width": 0.42, "edgecolor": "white", "linewidth": 1.5},
    )
    for indice, (angulo, x, y) in _posicoes_dos_rotulos(valores).items():
        _desenhar_rotulo_com_guia(ax, angulo, x, y, percentuais_reais[indice])

    # Espaço para as colunas de rótulos sem cortá-los na borda do eixo.
    ax.set_xlim(-_LIMITE_EIXO_ROSCA, _LIMITE_EIXO_ROSCA)
    ax.set_ylim(-_LIMITE_EIXO_ROSCA, _LIMITE_EIXO_ROSCA)
    # Precisa vir antes de medir a largura do buraco: `set_aspect` redefine a
    # escala px/unidade em X (o `ax` não é quadrado), e a medição usaria a
    # escala "auto" ainda vigente, superestimando em ~8% o espaço disponível.
    ax.set_aspect("equal")

    texto_total = _formatar_total(total)
    fonte_total = _fonte_total_ajustada_ao_buraco(fig, ax, texto_total, 22 * ESCALA_FONTE)
    ax.text(0, 0.12, texto_total, ha="center", va="center",
            fontsize=fonte_total, fontweight="bold", color="#3F3F3F")
    ax.text(0, -0.18, "domicílios", ha="center", va="center",
            fontsize=10*ESCALA_FONTE, color="#6B6B6B")

    ax.legend(
        wedges,
        rotulos_legenda,
        loc="center left",
        bbox_to_anchor=(1.04, 0.5),
        frameon=False,
        fontsize=12.75*ESCALA_FONTE,
        handlelength=1.0,
        handletextpad=0.5,
        labelspacing=0.6,
    )

    salvar_card_grafico(fig, chart_file)
    return chart_file.name


# Percentuais do perfil (esgoto_rede_*) já chegam como "68.4" (ponto decimal,
# não separador de milhar) ou Decimal — diferente das contagens de domicílios
# acima, que usam `_numero` (separador de milhar em ponto, decimal em vírgula).
# Reaproveitar `_numero` aqui trocaria "68.4" por 684.0, então este parser
# tenta o ponto como decimal primeiro e só cai pra vírgula-decimal depois.
# Devolve None (e não 0.0) quando não há número: 0% é um valor legítimo e
# frequente nestas colunas — 469 dos 2.074 municípios têm 0% em 2000 —, então
# quem chama precisa distinguir "zero" de "sem dado" (a view guarda o texto
# "sem dados" em alguns municípios).
def _numero_percentual(valor: object) -> float | None:
    if isinstance(valor, str):
        valor = valor.strip()
        try:
            numero = float(valor)
        except ValueError:
            try:
                numero = float(valor.replace(".", "").replace(",", "."))
            except ValueError:
                return None
    else:
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            return None
    return numero if math.isfinite(numero) else None


def _pontos_por_ano(
    cidade: dict, anos: tuple[tuple[str, str], ...]
) -> list[tuple[str, float]]:
    """Pares (rótulo do ano, percentual) dos anos que têm número na view.
    Ano ausente/"sem dados" fica de fora do gráfico; 0% entra como barra
    zerada, porque é cobertura real e não falta de dado."""
    pontos = []
    for chave, rotulo in anos:
        valor = _numero_percentual(cidade.get(chave))
        if valor is not None:
            pontos.append((rotulo, valor))
    return pontos


def _formatar_percentual(valor: float) -> str:
    return f"{valor:.2f}%".replace(".", ",")


# (chave no contexto, rótulo do ano) — ordem cronológica pedida no Doc.
_ANOS_DINAMICA_ESGOTO = (
    ("esgoto_rede_2000", "2000"),
    ("esgoto_rede_2010", "2010"),
    ("esgoto_rede_2022", "2022"),
)

# (chave no contexto, rótulo do ano) — ordem cronológica pedida no Doc.
_ANOS_COLETA_LIXO = (
    ("coleta_2010", "2010"),
    ("coleta_2022", "2022"),
)


def _barras_percentual_por_ano(
    titulo: str,
    pontos: list[tuple[str, float]],
    chart_file: pathlib.Path,
    altura_header: float = 0.14,
    figsize: tuple[float, float] = (8, 4.0),
    rotulo_y: str | None = None,
) -> None:
    anos = [rotulo for rotulo, _ in pontos]
    valores = [valor for _, valor in pontos]

    fig, ax = iniciar_card_grafico(figsize, titulo, altura_header=altura_header)
    # Reserva uma faixa abaixo do corpo do gráfico, dentro do card, para o
    # rótulo "Ano" (senão ele fica colado/cortado na borda inferior do card).
    posicao = ax.get_position()
    altura_rotulo_x = posicao.height * 0.12
    ax.set_position(
        (posicao.x0, posicao.y0 + altura_rotulo_x, posicao.width, posicao.height - altura_rotulo_x)
    )

    x = range(len(anos))
    barras = ax.bar(x, valores, width=0.78, color="#5B8DEF", zorder=3)
    limite = max(max(valores, default=0) * 1.22, 10)
    ax.set_ylim(0, limite)

    for barra, valor in zip(barras, valores):
        ax.text(
            barra.get_x() + barra.get_width() / 2,
            valor + limite * 0.025,
            _formatar_percentual(valor),
            ha="center",
            va="bottom",
            fontsize=FONTE_ROTULO_VALOR*ESCALA_FONTE,
            color="#3F3F3F",
        )

    ax.set_xticks(list(x))
    ax.set_xticklabels(anos, fontsize=FONTE_TICK*ESCALA_FONTE)
    ax.set_xlabel("Ano", fontsize=FONTE_ROTULO_EIXO*ESCALA_FONTE)
    if rotulo_y is not None:
        ax.set_ylabel(rotulo_y, fontsize=FONTE_ROTULO_EIXO*ESCALA_FONTE)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda valor, _: f"{valor:.0f}%"))
    ax.grid(axis="y", linestyle=(0, (2, 3)), linewidth=0.7, color="#D9D9D9", zorder=0)
    ax.tick_params(axis="both", length=0, labelsize=FONTE_TICK*ESCALA_FONTE, colors="#4A4A4A")
    for borda in ax.spines.values():
        borda.set_visible(False)

    salvar_card_grafico(fig, chart_file)


def gerar_grafico_dinamica_esgoto(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    pontos = _pontos_por_ano(cidade, _ANOS_DINAMICA_ESGOTO)
    if not pontos:
        raise ValueError("Dados de dinâmica de esgotamento não disponíveis.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_dinamica_esgoto_{safe_city}.png"
    reuso = reusar_grafico(chart_file)
    if reuso is not None:
        return reuso

    _barras_percentual_por_ano(
        "Domicílios conectados à rede geral de esgoto ou à rede pluvial",
        pontos,
        chart_file,
        rotulo_y="Percentual de domicílios",
    )
    return chart_file.name


def gerar_grafico_coleta_lixo(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    pontos = _pontos_por_ano(cidade, _ANOS_COLETA_LIXO)
    if not pontos:
        raise ValueError("Dados de coleta de lixo não disponíveis.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_coleta_lixo_{safe_city}.png"
    reuso = reusar_grafico(chart_file)
    if reuso is not None:
        return reuso

    _barras_percentual_por_ano(
        "Domicílios com coleta de lixo",
        pontos,
        chart_file,
        rotulo_y="Percentual de domicílios",
    )
    return chart_file.name
