"""Gráficos do relatório por área de interesse.

A área não reaproveita os adaptadores do estado (services/graficos_estado.py): as
funções de lá leem colunas `uf_*`, e a matview de área usa `area_*`. Por enquanto o
único gráfico de área é o de desenvolvimento social do Nordeste, de valores fixos.
"""

import logging
import pathlib
from collections.abc import Callable

from plotting.desenvolvimento_social import gerar_grafico_idhm_e_componentes

logger = logging.getLogger(__name__)

# INTENTIONAL: valores fixos, como o texto do Doc de área de desenvolvimento social
# (Rayane, 16/11/2026: o texto não tem placeholder, e o gráfico tem que dizer o mesmo
# que ele). Vêm da planilha "Fig 1.xlsx" da equipe e conferem com as medianas de
# des_idhm.idhm (nordeste = 'Sim', 1.794 municípios por ano) no gamma em 16/11/2026.
# Se o IDHM for atualizado, mudam aqui e no Doc juntos.
_ANOS_DO_IDHM = ("1991", "2000", "2010")
_MEDIANAS_DO_IDHM_NO_NORDESTE = {
    "IDHM": (0.291, 0.420, 0.588),
    "Longevidade": (0.556, 0.648, 0.7575),
    "Renda": (0.417, 0.477, 0.559),
    "Educação": (0.108, 0.238, 0.4825),
}

GeradorDeGraficoDaArea = Callable[[pathlib.Path, str], str]


def _grafico_idhm_do_nordeste(output_dir: pathlib.Path, safe_area: str) -> str:
    return gerar_grafico_idhm_e_componentes(
        _ANOS_DO_IDHM, _MEDIANAS_DO_IDHM_NO_NORDESTE, output_dir, safe_area
    )


# {(tema, área): {marcador do Doc: gerador}}. O marcador é o `*grafico_…` do Doc, sem
# o asterisco.
GRAFICOS_DA_AREA: dict[tuple[str, str], dict[str, GeradorDeGraficoDaArea]] = {
    ("desenvolvimento-social", "Nordeste"): {"grafico_idhm_componentes": _grafico_idhm_do_nordeste},
}


def gerar_graficos_da_area(
    slug: str, area: str, output_dir: pathlib.Path, safe_area: str
) -> dict[str, str]:
    """{marcador: arquivo PNG} dos gráficos do tema na área. Gráfico que falha
    (ValueError) fica de fora com aviso, e some do relatório junto com a menção
    "(Figura X)", como no estado.

    Ex.: gerar_graficos_da_area("desenvolvimento-social", "Nordeste", OUTPUT_DIR, "area_nordeste")
         == {"grafico_idhm_componentes": "grafico_idhm_componentes_area_nordeste.png"}
    """
    graficos: dict[str, str] = {}
    for marcador, gerar in GRAFICOS_DA_AREA.get((slug, area), {}).items():
        try:
            graficos[marcador] = gerar(output_dir, safe_area)
        except ValueError as err:
            logger.warning("Não foi possível gerar o gráfico de área '%s' para '%s': %s", marcador, area, err)

    return graficos
