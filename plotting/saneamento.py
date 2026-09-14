import itertools
import math
import pathlib

from matplotlib.ticker import FuncFormatter

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
# é empurrado para um raio maior, em vez de ser omitido: esconder o número
# de uma categoria que existe no dado é pior que um rótulo deslocado.
_ANGULO_MINIMO_ENTRE_ROTULOS = 15.0
# Raio (em frações do raio da rosca) onde os rótulos são escritos: o padrão e
# o "degrau" usado quando o rótulo vizinho está perto demais.
_RAIO_ROTULO = 1.18
_RAIO_ROTULO_AFASTADO = 1.40
# Abaixo deste percentual a fatia fica sem rótulo: o texto seria maior que a
# própria fatia e não haveria como ligá-lo a ela sem linha-guia. A categoria
# continua na legenda. Limiar herdado do gráfico original.
_PCT_MINIMO_PARA_ROTULO = 2.0


def _raios_dos_rotulos(valores: list[float]) -> dict[int, float]:
    """Raio de cada rótulo de percentual, por índice de fatia. Rótulos que
    ficariam colados no vizinho vão para um raio maior, alternadamente, de
    modo que nenhum seja omitido."""
    total = sum(valores)
    if total <= 0:
        return {}

    raios: dict[int, float] = {}
    angulo_acumulado = 0.0
    centro_anterior = None
    raio_anterior = _RAIO_ROTULO

    for indice, valor in enumerate(valores):
        angulo = 360.0 * valor / total
        centro = angulo_acumulado + angulo / 2
        angulo_acumulado += angulo

        if 100.0 * valor / total < _PCT_MINIMO_PARA_ROTULO:
            continue

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

    # Todas as fatias >= 2% recebem rótulo; quem ficaria colado no vizinho
    # é afastado radialmente (ver `_raios_dos_rotulos`), nunca omitido.
    raios_rotulos = _raios_dos_rotulos(valores)
    indice_fatia = itertools.count()

    def _autopct(pct: float) -> str:
        if next(indice_fatia) not in raios_rotulos:
            return ""
        return f"{pct:.1f}%".replace(".", ",")

    wedges, _textos, autotextos = ax.pie(
        valores,
        colors=cores,
        startangle=90,
        counterclock=False,
        autopct=_autopct,
        pctdistance=_RAIO_ROTULO,
        wedgeprops={"width": 0.42, "edgecolor": "white", "linewidth": 1.5},
    )
    # `pctdistance` é único para todas as fatias, então o degrau de quem está
    # apertado é aplicado aqui, reposicionando o texto no raio escolhido.
    for autotexto, raio in zip(
        autotextos, [raios_rotulos[i] for i in sorted(raios_rotulos)]
    ):
        x, y = autotexto.get_position()
        fator = raio / _RAIO_ROTULO
        autotexto.set_position((x * fator, y * fator))
        autotexto.set_fontsize(12)
        autotexto.set_color("#4A4A4A")

    # Espaço para o degrau externo dos rótulos sem cortá-los na borda do eixo.
    ax.set_xlim(-1.55, 1.55)
    ax.set_ylim(-1.55, 1.55)

    ax.text(0, 0.12, _formatar_total(total), ha="center", va="center",
            fontsize=22*ESCALA_FONTE, fontweight="bold", color="#3F3F3F")
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
    ax.set_aspect("equal")

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
    return f"{valor:.1f}%".replace(".", ",")


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
            fontsize=8.5*ESCALA_FONTE,
            color="#3F3F3F",
        )

    ax.set_xticks(list(x))
    ax.set_xticklabels(anos, fontsize=8.5*ESCALA_FONTE)
    ax.set_xlabel("Ano", fontsize=8.5*ESCALA_FONTE)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda valor, _: f"{valor:.0f}%"))
    ax.grid(axis="y", linestyle=(0, (2, 3)), linewidth=0.7, color="#D9D9D9", zorder=0)
    ax.tick_params(axis="both", length=0, labelsize=8.5*ESCALA_FONTE, colors="#4A4A4A")
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

    _barras_percentual_por_ano(
        # Título longo demais para uma linha no tamanho padrão do card (o
        # mesmo da Figura 3): quebra em duas e alarga a faixa do cabeçalho
        # para acomodá-las, em vez de diminuir a fonte. A quebra vai no
        # último ponto que ainda cabe na largura útil do cabeçalho (medida:
        # ~95% dela), pra não sobrar espaço vazio na primeira linha.
        "Dinâmica do percentual de domicílios conectados à rede geral de\n"
        "esgoto ou à rede pluvial",
        pontos,
        chart_file,
        altura_header=0.21,
        figsize=(8, 4.3),
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

    _barras_percentual_por_ano(
        "Evolução do percentual de domicílios com coleta de lixo",
        pontos,
        chart_file,
    )
    return chart_file.name
