"""Gráficos do relatório por estado: as mesmas funções de `plotting/`, alimentadas
pela linha da matview estadual (`uf_*`) em vez da linha do município.

Pedido de 12/11/2026: o Doc estadual já traz os marcadores `*grafico_...` com os
mesmos nomes do municipal. Em vez de copiar as funções de desenho, cada gráfico tem
um adaptador que monta, a partir das colunas `uf_*`, o dicionário que a função
municipal já sabe ler. Assim o gráfico do estado tem a mesma cara do municipal.

Diferenças de dado, decididas em 12/11/2026:
  - pirâmide etária: a matview tem 12 faixas (de 5 em 5 anos até 29, de 10 em 10
    depois). Em 12/11 a pirâmide usava as 12, porque era com elas que a matview
    calculava a "maior concentração" citada no texto. Em 13/11 a matview passou a
    calcular com faixas de 10 anos (D9), e o texto de MA, CE, AL e SE começou a
    citar "10 a 19 anos" ou "20 a 29 anos", barras que não existiam na figura (D16).
    Desde então o adaptador soma as faixas de 5 anos em faixas de 10 anos: são as 9
    faixas do municipal e as mesmas do texto;
  - dinâmica populacional: só 2010 e 2022, porque a matview não tem 2000.

Educação (12/11/2026) não tem diferença de dado: as 6 faixas de analfabetismo e os
4 níveis de instrução são os do municipal, nos 9 estados; só muda o nome da coluna.

Economia e Renda (12/11/2026): os adaptadores moram em
services/graficos_estado_economia.py (valores escalados da matview viram absolutos).

Saúde (12/11/2026): a est_saude não tem o público-alvo por faixa etária nem os
estabelecimentos de 2020 a 2023. Por decisão de 12/11, esses dois vêm somados por
estado das tabelas do painel (COMPLEMENTOS_DO_PAINEL); onde a matview também tem o
dado, a soma confere com ela. Infraestrutura (services/graficos_estado_saneamento.py)
faz o mesmo com a rosca de esgotamento, só quando a matview diz que a distribuição
está completa. Fora esses dois temas, tudo vem da matview.
"""

import logging
import pathlib
import re
from collections.abc import Callable
from dataclasses import dataclass

from plotting.demografia import (
    gerar_grafico_composicao_cor_raca,
    gerar_grafico_faixa_etaria_e_sexo,
    gerar_grafico_visao_historica_populacao,
)
from plotting.economia_renda import (
    gerar_grafico_balanca,
    gerar_grafico_exportacao,
    gerar_grafico_fob,
    gerar_grafico_pib,
    gerar_grafico_vab,
)
from plotting.educacao import (
    gerar_grafico_cor_faixa_etaria,
    gerar_grafico_nivel_instrucao,
)
from plotting.hidraulica import gerar_grafico_tecnologias_acesso_agua
from plotting.meio_ambiente import gerar_grafico_aridez_comparada
from plotting.saneamento import (
    gerar_grafico_coleta_lixo,
    gerar_grafico_dinamica_esgoto,
    gerar_grafico_esgotamento_sanitario,
)
from plotting.saude import (
    gerar_grafico_cobertura_vacinal,
    gerar_grafico_de_estabelecimento,
    gerar_grafico_publico_etario,
    gerar_grafico_taxa_mortalidade,
)
from services.graficos_estado_economia import (
    balanca_do_estado,
    exportacao_paises_do_estado,
    importacao_paises_do_estado,
    pib_serie_do_estado,
    vab_setores_do_estado,
)
from services.graficos_estado_saneamento import (
    coleta_lixo_do_estado,
    complemento_de_saneamento,
    dinamica_esgoto_do_estado,
    esgotamento_do_estado,
)
from utils.maps import normalizar_texto
from utils.queries.saude import (
    VACINA_COBERTURA_ROTULOS,
    buscar_estabelecimentos_saude_serie_estado,
    buscar_publico_etario_vacinas_estado,
)

logger = logging.getLogger(__name__)

_PREFIXO_FAIXA = "uf_faixa_etaria_2022_"
_POSICOES_COR_RACA = ("pri", "seg", "ter", "quar", "quin")
_ANOS_CENSO_ESTADO = (2010, 2022)
_NIVEIS_INSTRUCAO = ("pri_nivel", "seg_nivel", "ter_nivel", "quar_nivel")
# Rótulo da faixa na matview -> sufixo da coluna municipal `taxa_<faixa>_<cor>`.
_SUFIXO_POR_FAIXA_DE_ANALFABETISMO = {
    "15 a 19 anos": "15_a_19",
    "20 a 29 anos": "20_a_29",
    "30 a 39 anos": "30_a_39",
    "40 a 49 anos": "40_a_49",
    "50 a 59 anos": "50_a_59",
    "60 anos ou mais": "mais60",
}
_CORES_DO_ANALFABETISMO = ("branca", "preta", "amarela", "parda", "indigena")
# A matview reserva 8 posições de faixa (fx1…fx8); hoje fx7 e fx8 vêm vazias.
_POSICOES_DE_FAIXA_DE_ANALFABETISMO = range(1, 9)
# Colunas da est_saude com erro de digitação (12/11/2026). O nome certo é tentado
# primeiro, para uma correção na matview não tirar a vacina do gráfico.
_COLUNA_ALTERNATIVA_DA_VACINA = {"hepatite_b_30dias": "hebatite_b_30dias", "pneumo10": "penumo10"}
_FAIXAS_DO_PUBLICO_ETARIO = ("ao_nascer", "menor_1_ano", "1_ano", "multifaixa")


def _decada_da_faixa(sufixo: str) -> int:
    # "05_09" e "00_04" caem na década 0; "80_mais", na 80.
    return int(sufixo.split("_")[0]) // 10 * 10


def _soma_das_faixas(linha: dict, sexo: str, sufixos: list[str]) -> object:
    valores = [linha.get(f"uf_pop_faixa_{sexo}_2022_{sufixo}") for sufixo in sufixos]
    if all(valor is None for valor in valores):
        return None

    return sum(valor for valor in valores if valor is not None)


def faixas_etarias_sexo_do_estado(linha: dict) -> list[dict[str, object]]:
    """As faixas da pirâmide, da mais nova à mais velha, no formato de
    `faixas_etarias_sexo` do municipal, em faixas de 10 anos (D16, 13/11/2026):
    "0 a 4" + "5 a 9" viram "0 a 9 anos", e assim até 29. As faixas que a matview
    já tem de 10 anos ("30 a 39 anos", "80 anos ou mais") mantêm o rótulo dela.

    Ex.: faixas_etarias_sexo_do_estado(linha)[0]["faixa"] == "0 a 9 anos"
    """
    sufixos = sorted(
        chave.removeprefix(_PREFIXO_FAIXA) for chave in linha if chave.startswith(_PREFIXO_FAIXA)
    )
    sufixos_por_decada: dict[int, list[str]] = {}
    for sufixo in sufixos:
        sufixos_por_decada.setdefault(_decada_da_faixa(sufixo), []).append(sufixo)

    return [
        {
            "faixa": (
                linha[f"{_PREFIXO_FAIXA}{do_grupo[0]}"] if len(do_grupo) == 1 else f"{decada} a {decada + 9} anos"
            ),
            "mulheres": _soma_das_faixas(linha, "mulher", do_grupo),
            "homens": _soma_das_faixas(linha, "homem", do_grupo),
        }
        for decada, do_grupo in sufixos_por_decada.items()
    ]


def populacao_por_cor_raca_do_estado(linha: dict) -> dict[str, object]:
    """`pop_<cor>` e `pop_total_2022` como no municipal, a partir do ranking da
    matview (`uf_cor_raca_pri_class` + `uf_cor_pri_pop` … `uf_cor_quin_*`). A
    classe vem com acento ("indígena") e a chave municipal não tem ("pop_indigena").

    Ex.: populacao_por_cor_raca_do_estado(linha)["pop_parda"] == Decimal("2207880")
    """
    populacao: dict[str, object] = {"pop_total_2022": linha.get("uf_pop_total_2022")}
    for posicao in _POSICOES_COR_RACA:
        # A 1ª posição tem nome próprio na matview: uf_cor_raca_pri_class.
        coluna_classe = "uf_cor_raca_pri_class" if posicao == "pri" else f"uf_cor_{posicao}_class"
        classe = linha.get(coluna_classe)
        if not classe:
            continue
        populacao[f"pop_{normalizar_texto(classe)}"] = linha.get(f"uf_cor_{posicao}_pop")

    return populacao


def populacao_historica_do_estado(linha: dict) -> dict[str, object]:
    """`pop_total_<ano>` como no municipal, para os anos que a matview tem.

    Ex.: populacao_historica_do_estado(linha) == {"pop_total_2010": …, "pop_total_2022": …}
    """
    return {f"pop_total_{ano}": linha.get(f"uf_pop_total_{ano}") for ano in _ANOS_CENSO_ESTADO}


def niveis_de_instrucao_do_estado(linha: dict) -> dict[str, object]:
    """`<posição>_nivel_classe/per/pop` como no municipal: a matview só põe `uf_` na
    frente. Coluna que falta fica de fora, e a função municipal recusa o gráfico
    com a lista das ausentes.

    Ex.: niveis_de_instrucao_do_estado(linha)["pri_nivel_per"] == Decimal("47.49")
    """
    colunas = (f"{nivel}_{campo}" for nivel in _NIVEIS_INSTRUCAO for campo in ("classe", "per", "pop"))

    return {coluna: linha[f"uf_{coluna}"] for coluna in colunas if f"uf_{coluna}" in linha}


def taxas_de_analfabetismo_do_estado(linha: dict) -> dict[str, object]:
    """`taxa_<faixa>_<cor>` como no municipal. A matview numera as faixas (fx1…fx8)
    e dá o rótulo em `uf_analf_faixa_etaria_2022_fxN`; o casamento é pelo rótulo, e
    não pela posição, para uma faixa a mais ou fora de ordem não trocar as barras.
    Posição vazia ou rótulo desconhecido fica de fora; se faltar uma das 6 faixas,
    a função municipal recusa o gráfico.

    Ex.: taxas_de_analfabetismo_do_estado(linha)["taxa_mais60_preta"] == Decimal("50.21")
    """
    taxas: dict[str, object] = {}
    for posicao in _POSICOES_DE_FAIXA_DE_ANALFABETISMO:
        rotulo = linha.get(f"uf_analf_faixa_etaria_2022_fx{posicao}")
        sufixo = _SUFIXO_POR_FAIXA_DE_ANALFABETISMO.get(rotulo)
        if sufixo is None:
            continue
        for cor in _CORES_DO_ANALFABETISMO:
            taxas[f"taxa_{sufixo}_{cor}"] = linha.get(f"uf_analf_taxa_2022_{cor}_fx{posicao}")

    return taxas


def serie_anual_do_estado(linha: dict, campo: str) -> list[tuple[int, object]]:
    """(ano, valor) das colunas `uf_<campo>_<AAAA>`, em ordem de ano. Sufixo que não
    é ano (`uf_mortalidade_nordeste`) e valor nulo ficam de fora.

    Ex.: serie_anual_do_estado(linha, "mortalidade")[0] == (2010, Decimal("14.43"))
    """
    padrao = re.compile(rf"^uf_{campo}_(\d{{4}})$")
    anos = ((padrao.match(chave), valor) for chave, valor in linha.items())

    return sorted((int(achado.group(1)), valor) for achado, valor in anos if achado and valor is not None)


def mortalidade_infantil_serie_do_estado(linha: dict) -> dict[str, object]:
    """`mortalidade_infantil_serie` do municipal, com os anos que a matview tem
    (2010 e 2020 a 2025, os mesmos do municipal).

    Ex.: mortalidade_infantil_serie_do_estado(linha)["mortalidade_infantil_serie"][0]["ano"] == 2010
    """
    serie = [{"ano": ano, "taxa_mortalidade": taxa} for ano, taxa in serie_anual_do_estado(linha, "mortalidade")]

    return {"mortalidade_infantil_serie": serie}


def estabelecimentos_serie_do_estado(linha: dict) -> dict[str, object]:
    """`estabelecimentos_saude_serie` do municipal: a soma do painel (complemento)
    quando veio; se a consulta falhou, os anos da matview (2010, 2024 e 2025).

    Ex.: estabelecimentos_serie_do_estado(linha)["estabelecimentos_saude_serie"][0]["ano"] == 2010
    """
    if linha.get("estabelecimentos_saude_serie"):
        return {"estabelecimentos_saude_serie": linha["estabelecimentos_saude_serie"]}
    serie = [
        {"ano": ano, "total_estabelecimentos": total}
        for ano, total in serie_anual_do_estado(linha, "estabelecimento")
    ]

    return {"estabelecimentos_saude_serie": serie}


def _coluna_da_vacina(linha: dict, campo: str) -> str | None:
    for nome in (campo, _COLUNA_ALTERNATIVA_DA_VACINA.get(campo)):
        if nome and linha.get(f"uf_{nome}") is not None:
            return f"uf_{nome}"

    return None


def cobertura_vacinal_serie_do_estado(linha: dict) -> dict[str, object]:
    """`cobertura_vacinal_serie` do municipal: as mesmas vacinas e rótulos
    (VACINA_COBERTURA_ROTULOS), lidas de `uf_<vacina>` e `uf_<vacina>_meta`.

    Ex.: cobertura_vacinal_serie_do_estado(linha)["cobertura_vacinal_serie"][0]["vacina"] == "BCG"
    """
    serie = []
    for campo, rotulo in VACINA_COBERTURA_ROTULOS:
        coluna = _coluna_da_vacina(linha, campo)
        if coluna is None:
            continue
        serie.append({"vacina": rotulo, "cobertura_vacinal": linha[coluna], "meta": linha.get(f"{coluna}_meta")})

    return {"cobertura_vacinal_serie": serie}


def publico_etario_do_estado(linha: dict) -> dict[str, object]:
    """Público-alvo e doses por faixa, com as chaves do municipal. Vêm do complemento
    do painel; sem ele, ValueError com as chaves que faltam (o gráfico fica de fora).

    Ex.: publico_etario_do_estado(linha)["publico_etario_1_ano"] == Decimal("395008")
    """
    chaves = [f"{tipo}_etario_{faixa}" for tipo in ("publico", "dose") for faixa in _FAIXAS_DO_PUBLICO_ETARIO]
    faltando = [chave for chave in chaves if linha.get(chave) is None]
    if faltando:
        raise ValueError(
            f"Público-alvo etário do estado indisponível: faltam {faltando}; esperava a soma "
            "da view do painel (buscar_publico_etario_vacinas_estado)."
        )

    return {chave: linha[chave] for chave in chaves}


def tecnologias_acesso_agua_do_estado(linha: dict) -> dict[str, object]:
    """`tecnologias_acesso_agua_serie` e `total_2025` do municipal, com os anos de
    `uf_total_<AAAA>`: 2010, 2020 e 2025, os da legenda do Doc estadual. O municipal
    mostra também 2021 a 2024; por decisão de 12/11/2026 o estado fica com os 3 anos
    da matview.

    Ex.: tecnologias_acesso_agua_do_estado(linha)["tecnologias_acesso_agua_serie"][0] == {"ano": 2010, …}
    """
    serie = [{"ano": ano, "total": total} for ano, total in serie_anual_do_estado(linha, "total")]

    return {"tecnologias_acesso_agua_serie": serie, "total_2025": linha.get("uf_total_2025")}


def aridez_do_estado(linha: dict) -> dict[str, object]:
    """As colunas de aridez sem o prefixo `uf_` (`area_semiarida2021_per`,
    `aridez_1991_valida`…), que é o que gerar_grafico_aridez_comparada lê.

    Ex.: aridez_do_estado(linha)["area_semiarida2021_per"] == Decimal("83.62")
    """
    return {
        chave.removeprefix("uf_"): valor
        for chave, valor in linha.items()
        if chave.startswith(("uf_area_", "uf_aridez_"))
    }


def _grafico_faixa_etaria(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    cidade = {"faixas_etarias_sexo": faixas_etarias_sexo_do_estado(linha)}

    return gerar_grafico_faixa_etaria_e_sexo(cidade, output_dir, safe_estado)


def _grafico_cor_raca(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_composicao_cor_raca(populacao_por_cor_raca_do_estado(linha), output_dir, safe_estado)


def _grafico_visao_historica(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_visao_historica_populacao(
        populacao_historica_do_estado(linha), output_dir, safe_estado, anos_censo=_ANOS_CENSO_ESTADO
    )


def _grafico_nivel_instrucao(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_nivel_instrucao(niveis_de_instrucao_do_estado(linha), output_dir, safe_estado)


def _grafico_analfabetismo(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_cor_faixa_etaria(taxas_de_analfabetismo_do_estado(linha), output_dir, safe_estado)


def _grafico_publico_etario(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_publico_etario(publico_etario_do_estado(linha), output_dir, safe_estado)


def _grafico_cobertura_vacinal(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_cobertura_vacinal(cobertura_vacinal_serie_do_estado(linha), output_dir, safe_estado)


def _grafico_mortalidade(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_taxa_mortalidade(mortalidade_infantil_serie_do_estado(linha), output_dir, safe_estado)


def _grafico_tecnologias_acesso_agua(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_tecnologias_acesso_agua(tecnologias_acesso_agua_do_estado(linha), output_dir, safe_estado)


def _grafico_aridez(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_aridez_comparada(aridez_do_estado(linha), output_dir, safe_estado)


def _grafico_pib(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_pib(pib_serie_do_estado(linha), output_dir, safe_estado)


def _grafico_vab(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_vab(vab_setores_do_estado(linha), output_dir, safe_estado)


def _grafico_importacao(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_fob(importacao_paises_do_estado(linha), output_dir, safe_estado)


def _grafico_exportacao(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_exportacao(exportacao_paises_do_estado(linha), output_dir, safe_estado)


def _grafico_balanca(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_balanca(balanca_do_estado(linha), output_dir, safe_estado)


def _grafico_estabelecimentos(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_de_estabelecimento(estabelecimentos_serie_do_estado(linha), output_dir, safe_estado)


def _grafico_dinamica_esgoto(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_dinamica_esgoto(dinamica_esgoto_do_estado(linha), output_dir, safe_estado)


def _grafico_esgotamento(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_esgotamento_sanitario(esgotamento_do_estado(linha), output_dir, safe_estado)


def _grafico_coleta_lixo(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_coleta_lixo(coleta_lixo_do_estado(linha), output_dir, safe_estado)


@dataclass(frozen=True)
class GraficoDoEstado:
    """Um gráfico estadual: o marcador `*<placeholder>` do Doc e a função que o gera."""

    placeholder: str
    gerar: Callable[[dict, pathlib.Path, str], str]


# Mesmos placeholders de GRAFICOS_POR_TEMA (services/generation.py): o Doc estadual
# usa os nomes do municipal. Tema fora daqui sai sem gráficos, como antes.
GRAFICOS_ESTADO_POR_TEMA: dict[str, tuple[GraficoDoEstado, ...]] = {
    "demografia": (
        GraficoDoEstado("grafico_faixa_etaria_e_sexo", _grafico_faixa_etaria),
        GraficoDoEstado("grafico_composicao_cor_raca", _grafico_cor_raca),
        GraficoDoEstado("grafico_visao_historica", _grafico_visao_historica),
    ),
    "educacao": (
        GraficoDoEstado("grafico_cor_faixa_etaria", _grafico_analfabetismo),
        GraficoDoEstado("grafico_nivel_instrucao", _grafico_nivel_instrucao),
    ),
    "economia-renda": (
        GraficoDoEstado("grafico_pib", _grafico_pib),
        GraficoDoEstado("grafico_vab", _grafico_vab),
        GraficoDoEstado("grafico_fob", _grafico_importacao),
        GraficoDoEstado("grafico_exportacao", _grafico_exportacao),
        GraficoDoEstado("grafico_balanca", _grafico_balanca),
    ),
    "hidraulica": (
        GraficoDoEstado("grafico_tecnologias_acesso_agua", _grafico_tecnologias_acesso_agua),
    ),
    # Único gráfico que o municipal não tem: o Doc estadual compara 1991 e 2021
    # (decisão de 12/11/2026) com um marcador próprio.
    "meio-ambiente": (
        GraficoDoEstado("grafico_aridez_estadual", _grafico_aridez),
    ),
    "saude": (
        GraficoDoEstado("grafico_publico_etario", _grafico_publico_etario),
        GraficoDoEstado("grafico_cobertura_vacinal", _grafico_cobertura_vacinal),
        GraficoDoEstado("grafico_taxa_mortalidade", _grafico_mortalidade),
        GraficoDoEstado("grafico_de_estabelecimento", _grafico_estabelecimentos),
    ),
    "saneamento": (
        GraficoDoEstado("grafico_domicilio", _grafico_dinamica_esgoto),
        GraficoDoEstado("grafico_domicilio_por_tipo_esgosto", _grafico_esgotamento),
        GraficoDoEstado("grafico_coleta_lixo", _grafico_coleta_lixo),
    ),
}


def _complemento_de_saude(linha: dict) -> dict[str, object]:
    sigla_uf = str(linha.get("uf_sigla_uf") or "")
    publico_etario = buscar_publico_etario_vacinas_estado(sigla_uf) or {}
    estabelecimentos = buscar_estabelecimentos_saude_serie_estado(sigla_uf) or {}

    return {**publico_etario, **estabelecimentos}


# Dados que a matview do tema não tem e que o gráfico precisa, somados por estado
# nas tabelas do painel (decisão de 12/11/2026). Recebe a linha da matview, para
# poder decidir se precisa consultar (saneamento só consulta com a flag em 1).
ComplementoDoPainel = Callable[[dict], dict[str, object]]
COMPLEMENTOS_DO_PAINEL: dict[str, ComplementoDoPainel] = {
    "saude": _complemento_de_saude,
    "saneamento": complemento_de_saneamento,
}


def gerar_graficos_do_estado(
    slug: str,
    linha: dict,
    output_dir: pathlib.Path,
    safe_estado: str,
    complementos: dict[str, ComplementoDoPainel] = COMPLEMENTOS_DO_PAINEL,
) -> dict[str, str]:
    """{placeholder: arquivo PNG} dos gráficos do tema para o estado. Gráfico sem
    dado (a função levanta ValueError) fica de fora, com aviso no log, e some do
    relatório junto com a menção "(Figura X)", como no municipal. `complementos`
    é a costura dos testes para as consultas ao painel.

    Ex.: gerar_graficos_do_estado("demografia", linha, OUTPUT_DIR, "estado_para_ba")
    """
    complementar = complementos.get(slug)
    if complementar is not None:
        linha = {**linha, **complementar(linha)}
    graficos: dict[str, str] = {}
    for grafico in GRAFICOS_ESTADO_POR_TEMA.get(slug, ()):
        try:
            graficos[grafico.placeholder] = grafico.gerar(linha, output_dir, safe_estado)
        except ValueError as err:
            logger.warning(
                "Não foi possível gerar o gráfico estadual '%s' para '%s': %s",
                grafico.placeholder, safe_estado, err,
            )

    return graficos
