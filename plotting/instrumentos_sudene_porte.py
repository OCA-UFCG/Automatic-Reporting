"""Gráficos de porte da empresa do macrotema Instrumentos da Sudene (FNE, 2025).

Dois cards de pizza que o Doc põe lado a lado com o marcador
`*grafico_porte_contratacoes+grafico_porte_valor`, acima da legenda "Percentual de
contratação e de valor investido por porte da empresa".

A view `relatorios_auto.instrsudene_munic` já entrega o percentual de cada porte
(`contrato_<porte>` e `valor_<porte>`, somando ~100). Recife/PE em 2025:
micro 72,54% das contratações, pequeno 41,29% do valor.
"""

import math
import pathlib

from matplotlib.colors import to_rgb

from plotting import (
    ESCALA_FONTE,
    FONTE_ROTULO_VALOR,
    iniciar_card_grafico,
    reusar_grafico,
    salvar_card_grafico,
)
from plotting.saneamento import _angulos_dos_meios, _posicoes_dos_rotulos
from utils.formatting import formatar_numero_ptbr

# (sufixo da coluna na view, rótulo). INTENTIONAL: ordem alfabética, como no
# design do Figma; a pizza começa às 12 horas e anda no sentido horário.
PORTES_EMPRESA = (
    ("grande", "Grande"),
    ("media1", "Médio I"),
    ("media2", "Médio II"),
    ("micro", "Micro"),
    ("mini", "Mini"),
    ("pequeno", "Pequeno"),
    ("peq_medio", "Pequeno-Médio"),
)
# Cores medidas do design, na ordem de `PORTES_EMPRESA`.
_CORES_CONTRATACOES = ("#5C2508", "#FFBE20", "#B75006", "#F99C07", "#7A330D", "#FFD65A", "#DD7402")
_CORES_VALOR = ("#00BD47", "#04E35B", "#085F2D", "#018F39", "#0B3D22", "#2EFA7D", "#B0FFCF")
_COR_GUIA = "#7A7A7A"
_COR_TEXTO_ESCURO = "#292829"
_COR_TEXTO_CLARO = "#FFFFFF"
# Raios (fração do raio da pizza) onde o rótulo de dentro é tentado, em ordem:
# a posição de costume, depois mais perto do centro (rótulo alto, de três
# linhas) e por último mais perto da borda, onde a fatia é mais larga.
_RAIOS_ROTULO_DENTRO = (0.6, 0.5, 0.72)
# Escalas da fonte tentadas para o rótulo de dentro, em ordem. A menor só entra
# quando o rótulo não cabe no tamanho normal: "Pequeno-/Médio/33%" (Recife/PE)
# tem ~0,8 x 0,6 raio e sai do círculo em qualquer posição da fatia.
_ESCALAS_FONTE_DENTRO = (1.0, 0.85)
# Folga entre o texto e a borda da fatia: em graus (lados) e em raios (arco).
_FOLGA_ANGULAR_GRAUS = 2.0
_RAIO_MAXIMO_TEXTO = 0.96
# IMPORTANT: no relatório os dois cards dividem a largura da página
# (`*grafico_porte_contratacoes+grafico_porte_valor`), então o PNG sai com menos
# da metade do tamanho de um gráfico sozinho. Card quase quadrado e pizza
# ocupando a maior parte dele fazem a fonte e as fatias chegarem legíveis ao PDF.
_TAMANHO_CARD = (4.4, 4.0)
# Meia-largura/altura do eixo, em raios da pizza: cabe a coluna de rótulos de
# fora de `_posicoes_dos_rotulos` (x = ±1,30) mais um rótulo curto ("Médio II").
_LIMITE_EIXO_X = 2.05
# Assimétrico: os rótulos de fora sobem até y = 1,45 (`_posicoes_dos_rotulos`)
# com até três linhas, mas embaixo da pizza quase nunca há rótulo; simétrico,
# sobrava uma faixa vazia sob a pizza.
_LIMITES_EIXO_Y = (-1.2, 1.75)
# Distância vertical entre rótulos de fora, em raios: cabe "Pequeno-/Médio/1%"
# em três linhas (o padrão de `_posicoes_dos_rotulos` cabe uma linha só; com
# 0,42 ele encavalava no "Pequeno" logo abaixo em Igaci/AL).
_ESPACO_ROTULO_FORA = 0.56


def percentuais_por_porte(cidade: dict, prefixo: str) -> list[float]:
    """Percentual de cada porte em `PORTES_EMPRESA`, lido de `<prefixo><porte>`.

    Ex.: percentuais_por_porte(recife, "contrato_")[3] -> 72.54 (micro).
    """
    chaves = [f"{prefixo}{porte}" for porte, _ in PORTES_EMPRESA]
    faltando = [chave for chave in chaves if cidade.get(chave) is None]
    if faltando:
        raise ValueError(f"Percentuais por porte ausentes: {faltando}; esperado número em cada coluna.")

    percentuais = [float(cidade[chave]) for chave in chaves]
    if sum(percentuais) <= 0:
        raise ValueError(f"Percentuais por porte zerados em '{prefixo}*': {percentuais}.")

    return percentuais


def _texto_do_rotulo(indice: int, percentual: float) -> str:
    # Percentual inteiro, como no design ("72%"); o texto do Doc é que traz as
    # duas casas. "Pequeno-Médio" quebra no hífen para caber na fatia.
    nome = PORTES_EMPRESA[indice][1].replace("-", "-\n")

    return f"{nome}\n{formatar_numero_ptbr(percentual)}%"


def _cor_do_texto_sobre(cor_fatia: str) -> str:
    # Luminância relativa (sRGB simplificado): texto branco só em fatia escura.
    r, g, b = to_rgb(cor_fatia)
    luminancia = 0.2126 * r + 0.7152 * g + 0.0722 * b

    return _COR_TEXTO_CLARO if luminancia < 0.45 else _COR_TEXTO_ESCURO


def faixas_angulares(percentuais: list[float]) -> dict[int, tuple[float, float]]:
    """(ângulo inicial, ângulo final), em graus, de cada fatia > 0, na geometria
    de `ax.pie(startangle=90, counterclock=False)`: o final é menor que o inicial.
    Ex.: [25, 75] -> {0: (90, 0), 1: (0, -270)}."""
    total = sum(percentuais)
    faixas: dict[int, tuple[float, float]] = {}
    acumulado = 0.0
    for indice, pct in enumerate(percentuais):
        if pct > 0:
            faixas[indice] = (90 - 360 * acumulado / total, 90 - 360 * (acumulado + pct) / total)
        acumulado += pct

    return faixas


def ponto_dentro_da_fatia(x: float, y: float, faixa: tuple[float, float]) -> bool:
    """O ponto (em raios) está dentro da fatia, com folga das bordas?"""
    inicio, fim = faixa
    if math.hypot(x, y) > _RAIO_MAXIMO_TEXTO:
        return False

    # Quanto o ponto anda, no sentido horário, a partir do início da fatia.
    percorrido = (inicio - math.degrees(math.atan2(y, x))) % 360

    return _FOLGA_ANGULAR_GRAUS <= percorrido <= (inicio - fim) - _FOLGA_ANGULAR_GRAUS


def _texto_cabe_na_fatia(ax, texto, faixa: tuple[float, float]) -> bool:
    caixa = texto.get_window_extent(renderer=ax.figure.canvas.get_renderer())
    cantos = [(caixa.x0, caixa.y0), (caixa.x0, caixa.y1), (caixa.x1, caixa.y0), (caixa.x1, caixa.y1)]
    cantos_em_raios = ax.transData.inverted().transform(cantos)

    return all(ponto_dentro_da_fatia(x, y, faixa) for x, y in cantos_em_raios)


def _desenhar_rotulos_dentro(ax, percentuais: list[float], cores: tuple[str, ...]) -> set[int]:
    """Põe dentro da fatia o rótulo que cabe nela e devolve os índices rotulados.

    WARNING: não volte a decidir só pelo percentual. "Pequeno 18%" (Recife/PE)
    passava da borda da fatia: o que importa é a largura do nome e a direção da
    fatia, e isso só a caixa do texto desenhado diz.
    """
    faixas = faixas_angulares(percentuais)
    rotulados: set[int] = set()
    for indice, angulo in _angulos_dos_meios(percentuais).items():
        if _encaixar_rotulo_dentro(ax, indice, angulo, percentuais[indice], cores[indice], faixas[indice]):
            rotulados.add(indice)

    return rotulados


def _encaixar_rotulo_dentro(
    ax, indice: int, angulo: float, percentual: float, cor: str, faixa: tuple[float, float]
) -> bool:
    rad = math.radians(angulo)
    for escala in _ESCALAS_FONTE_DENTRO:
        for raio in _RAIOS_ROTULO_DENTRO:
            texto = ax.text(
                raio * math.cos(rad), raio * math.sin(rad), _texto_do_rotulo(indice, percentual),
                ha="center", va="center", linespacing=1.05, fontweight="semibold",
                fontsize=FONTE_ROTULO_VALOR * ESCALA_FONTE * escala, color=_cor_do_texto_sobre(cor),
            )
            if _texto_cabe_na_fatia(ax, texto, faixa):
                return True
            texto.remove()

    return False


def _desenhar_rotulos_fora(ax, percentuais: list[float], indices: set[int]) -> None:
    # Linha-guia com cotovelo, como na rosca de esgotamento (plotting/saneamento.py):
    # sai radialmente da borda da fatia e segue na horizontal até o texto.
    for indice, (angulo, x, y) in _posicoes_dos_rotulos(percentuais, _ESPACO_ROTULO_FORA, indices).items():
        rad = math.radians(angulo)
        borda = (math.cos(rad), math.sin(rad))
        cotovelo = (1.08 * borda[0], 1.08 * borda[1])
        lado = 1 if x > 0 else -1
        ax.plot(
            [borda[0], cotovelo[0], x - lado * 0.04], [borda[1], cotovelo[1], y],
            color=_COR_GUIA, linewidth=0.8, solid_capstyle="round",
        )
        ax.text(
            x, y, _texto_do_rotulo(indice, percentuais[indice]), ha="left" if lado == 1 else "right",
            va="center", linespacing=1.05, fontsize=FONTE_ROTULO_VALOR * ESCALA_FONTE,
            fontweight="semibold", color=_COR_TEXTO_ESCURO,
        )


def _desenhar_pizza_por_porte(
    titulo: str, percentuais: list[float], cores: tuple[str, ...], chart_file: pathlib.Path
) -> None:
    fig, ax = iniciar_card_grafico(_TAMANHO_CARD, titulo, margem_esquerda=0.03)
    # Fatia de 0% não é desenhada nem rotulada (`_angulos_dos_meios` só devolve
    # fatias > 0): não há o que apontar. Fatia fina > 0 continua, mesmo que o
    # inteiro arredonde para "0%" (Grande 0,37% em Recife), como no design.
    ax.pie(
        percentuais, colors=cores, startangle=90, counterclock=False,
        wedgeprops={"edgecolor": "white", "linewidth": 1.2},
    )
    # Limites e aspecto antes dos rótulos: medir se o texto cabe na fatia
    # depende da escala final (polegadas por raio).
    ax.set_xlim(-_LIMITE_EIXO_X, _LIMITE_EIXO_X)
    ax.set_ylim(*_LIMITES_EIXO_Y)
    ax.set_aspect("equal")
    ax.apply_aspect()
    dentro = _desenhar_rotulos_dentro(ax, percentuais, cores)
    fora = {i for i, pct in enumerate(percentuais) if pct > 0 and i not in dentro}
    _desenhar_rotulos_fora(ax, percentuais, fora)
    salvar_card_grafico(fig, chart_file)


def _gerar_grafico_porte(
    cidade: dict, output_dir: pathlib.Path, safe_city: str, tipo: str
) -> str:
    prefixo, titulo, cores = _TIPOS_GRAFICO_PORTE[tipo]
    percentuais = percentuais_por_porte(cidade, prefixo)
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_file = output_dir / f"grafico_porte_{tipo}_{safe_city}.png"
    reuso = reusar_grafico(chart_file)
    if reuso is not None:
        return reuso

    _desenhar_pizza_por_porte(titulo, percentuais, cores, chart_file)
    return chart_file.name


# tipo -> (prefixo da coluna na view, título do card, cores por porte).
_TIPOS_GRAFICO_PORTE = {
    "contratacoes": ("contrato_", "Total de contratações", _CORES_CONTRATACOES),
    "valor": ("valor_", "Valor total investido", _CORES_VALOR),
}


def gerar_grafico_porte_contratacoes(cidade: dict, OUTPUT_DIR: pathlib.Path, safe_city: str) -> str:
    return _gerar_grafico_porte(cidade, OUTPUT_DIR, safe_city, "contratacoes")


def gerar_grafico_porte_valor(cidade: dict, OUTPUT_DIR: pathlib.Path, safe_city: str) -> str:
    return _gerar_grafico_porte(cidade, OUTPUT_DIR, safe_city, "valor")
