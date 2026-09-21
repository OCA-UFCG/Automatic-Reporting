import itertools
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


# Distância angular mínima, em graus, entre os centros de dois rótulos de
# percentual vizinhos para que caibam no mesmo raio. Abaixo disso o de fora
# é empurrado para um raio maior — rede de segurança para distribuições que
# escapem do ajuste de ângulo abaixo.
_ANGULO_MINIMO_ENTRE_ROTULOS = 15.0
# Raio (em frações do raio da rosca) onde os rótulos são escritos: o padrão e
# o "degrau" usado quando o rótulo vizinho está perto demais.
_RAIO_ROTULO = 1.18
_RAIO_ROTULO_AFASTADO = 1.40
# Ângulo mínimo de desenho de cada fatia, em graus. AJUSTE VISUAL: a fatia
# dominante (83,4% em Belém/AL, por exemplo) é desenhada menor que a sua
# proporção real para as fatias pequenas aparecerem e caberem seus rótulos.
# Os percentuais escritos continuam sendo os reais — só o desenho é ajustado.
# Precisa ser maior que `_ANGULO_MINIMO_ENTRE_ROTULOS`: duas fatias no piso
# ficam a exatamente este ângulo uma da outra, e é essa folga que garante
# que todo rótulo caiba ao lado da sua fatia, sem ser empurrado para fora.
_ANGULO_MINIMO_DA_FATIA = 16.0


def _angulos_de_desenho(valores: list[float]) -> list[float]:
    """Ângulos usados para DESENHAR as fatias: cada categoria com valor > 0
    recebe um piso de `_ANGULO_MINIMO_DA_FATIA` e o resto do círculo é
    repartido proporcionalmente. Mantém a ordem e o ranking das fatias; os
    percentuais dos rótulos continuam vindo dos valores reais."""
    total = sum(valores)
    if total <= 0:
        return list(valores)

    com_valor = [valor > 0 for valor in valores]
    piso_total = _ANGULO_MINIMO_DA_FATIA * sum(com_valor)
    # Se os pisos já consomem o círculo (muitas categorias), cai para a
    # proporção real — melhor um desenho apertado que um sem ordenação.
    if piso_total >= 360.0:
        return list(valores)

    restante = 360.0 - piso_total
    return [
        (_ANGULO_MINIMO_DA_FATIA + restante * valor / total) if tem else 0.0
        for valor, tem in zip(valores, com_valor)
    ]


def _raios_dos_rotulos(angulos: list[float]) -> dict[int, float]:
    """Raio de cada rótulo de percentual, por índice de fatia. Recebe os
    ângulos de DESENHO (é a geometria do anel que decide se dois rótulos
    colidem). Quem ficaria colado no vizinho vai para um raio maior."""
    total = sum(angulos)
    if total <= 0:
        return {}

    raios: dict[int, float] = {}
    angulo_acumulado = 0.0
    centro_anterior = None
    raio_anterior = _RAIO_ROTULO

    for indice, angulo in enumerate(angulos):
        if angulo <= 0:
            continue
        centro = angulo_acumulado + angulo / 2
        angulo_acumulado += angulo

        perto_do_anterior = (
            centro_anterior is not None
            and centro - centro_anterior < _ANGULO_MINIMO_ENTRE_ROTULOS
        )
        # Só alterna se o anterior estava no raio de dentro: três rótulos
        # seguidos e próximos ficam dentro/fora/dentro, nunca dois fora
        # colados um no outro.
        raio = (
            _RAIO_ROTULO_AFASTADO
            if perto_do_anterior and raio_anterior == _RAIO_ROTULO
            else _RAIO_ROTULO
        )
        raios[indice] = raio
        centro_anterior = centro
        raio_anterior = raio

    return raios


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

    # AJUSTE VISUAL das fatias: o desenho usa ângulos com piso mínimo (ver
    # `_angulos_de_desenho`), não a proporção crua — assim as fatias pequenas
    # aparecem e cada rótulo fica junto da sua fatia. Os percentuais escritos
    # vêm dos valores REAIS, calculados aqui e não pelo `autopct` do
    # matplotlib (que os derivaria dos ângulos ajustados).
    angulos = _angulos_de_desenho(valores)
    percentuais_reais = [100.0 * valor / total for valor in valores]
    raios_rotulos = _raios_dos_rotulos(angulos)
    indice_fatia = itertools.count()

    def _autopct(_pct_do_desenho: float) -> str:
        indice = next(indice_fatia)
        if indice not in raios_rotulos:
            return ""
        return f"{percentuais_reais[indice]:.2f}%".replace(".", ",")

    wedges, _textos, autotextos = ax.pie(
        angulos,
        colors=cores,
        startangle=90,
        counterclock=False,
        autopct=_autopct,
        pctdistance=_RAIO_ROTULO,
        wedgeprops={"width": 0.42, "edgecolor": "white", "linewidth": 1.5},
    )
    # `pctdistance` é único para todas as fatias, então o degrau de quem ficou
    # apertado é aplicado aqui, reposicionando o texto no raio escolhido.
    for autotexto, raio in zip(
        autotextos, [raios_rotulos[i] for i in sorted(raios_rotulos)]
    ):
        x, y = autotexto.get_position()
        fator = raio / _RAIO_ROTULO
        autotexto.set_position((x * fator, y * fator))
        autotexto.set_fontsize(FONTE_ROTULO_VALOR * ESCALA_FONTE)
        autotexto.set_color("#4A4A4A")

    # Espaço para o degrau externo dos rótulos sem cortá-los na borda do eixo.
    ax.set_xlim(-1.55, 1.55)
    ax.set_ylim(-1.55, 1.55)
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
