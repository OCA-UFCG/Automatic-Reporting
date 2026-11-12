"""Adaptadores dos gráficos de Economia e Renda no relatório por estado (12/11/2026).

Mesma ideia de services/graficos_estado.py: montar, a partir da linha `uf_*` da
est_economia, o que as funções de plotting/economia_renda.py já leem. A diferença
é de formato. As funções municipais recebem valores absolutos (reais ou US$), e a
matview guarda a maior parte deles escalada, com a unidade ao lado
(`uf_pib_2023` = 96,96 e `uf_pib_unid_2023` = "bilhões"). Os países e os saldos
mensais já vêm absolutos, em listas e colunas por mês.

Decisão de 12/11/2026: os rankings de países mostram o mesmo número do municipal,
10 na importação e 4 na exportação, embora a matview traga a lista inteira.
"""

import re

from utils.maps import normalizar_texto
from utils.queries.economia_exportacao import UNIDADE_MULTIPLICADOR

_PAISES_NA_IMPORTACAO = 10
_PAISES_NA_EXPORTACAO = 4
_ABREVIACOES_DOS_MESES = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez")
_ANO_DO_PIB = re.compile(r"^uf_pib_(\d{4})$")
# O nome do setor vem com a preposição do texto ("de Serviços", "da Indústria").
_PREPOSICAO_DO_SETOR = re.compile(r"^(?:de|da|do)\s+")
_CHAVE_POR_SETOR = {
    "servicos": "servicos",
    "industria": "industria",
    "administracao publica": "adm_publica",
    "agropecuaria": "agropecuaria",
}
# (coluna do nome, coluna do valor, coluna da unidade) de cada posição do ranking.
_COLUNAS_DOS_SETORES = (
    ("uf_setor2021_maior1", "uf_valor_setor2021_maior1", "uf_setor2021_maior1unid"),
    ("uf_setor2021_maior2", "uf_valor_setor2021_maior2", "uf_setor2021_maior2unid"),
    ("uf_setor2021_maior3", "uf_valor_setor2021_maior3", "uf_setor2021_maior3unid"),
    ("uf_setor2021_menor", "uf_valor_setor2021_menor", "uf_setor2021_menor_unid"),
)


def valor_absoluto_do_estado(valor: object, unidade: object) -> float:
    """Desfaz a escala da matview: 96,96 "bilhões" vira 96.960.000.000. Unidade
    vazia vale 1. Unidade desconhecida levanta ValueError (o gráfico fica de fora),
    porque um multiplicador errado desenharia o valor 1.000 vezes menor sem erro.

    Ex.: valor_absoluto_do_estado(Decimal("96.96"), "bilhões") == 96_960_000_000.0
    """
    if unidade in (None, ""):
        return float(valor)
    if unidade not in UNIDADE_MULTIPLICADOR:
        raise ValueError(
            f"Unidade {unidade!r} desconhecida no valor {valor}; esperava uma de "
            f"{sorted(UNIDADE_MULTIPLICADOR)} ou vazia."
        )

    return float(valor) * UNIDADE_MULTIPLICADOR[unidade]


def pib_serie_do_estado(linha: dict) -> dict[str, object]:
    """`pib_serie` do municipal, em reais, com os anos de `uf_pib_<AAAA>` (2010 a
    2023 nos 9 estados, os mesmos do municipal).

    Ex.: pib_serie_do_estado(linha)["pib_serie"][-1] == {"ano": 2023, "pib_total": 96_960_000_000.0}
    """
    anos = sorted(
        int(achado.group(1))
        for chave, valor in linha.items()
        if (achado := _ANO_DO_PIB.match(chave)) and valor is not None
    )
    serie = [
        {"ano": ano, "pib_total": valor_absoluto_do_estado(linha[f"uf_pib_{ano}"], linha.get(f"uf_pib_unid_{ano}"))}
        for ano in anos
    ]

    return {"pib_serie": serie}


def _chave_do_setor(nome: object) -> str | None:
    return _CHAVE_POR_SETOR.get(_PREPOSICAO_DO_SETOR.sub("", normalizar_texto(nome)))


def vab_setores_do_estado(linha: dict) -> dict[str, object]:
    """`vab_setores_2021` do municipal, em reais, a partir do ranking da matview
    (3 maiores e o menor). Exige os 4 setores: com um faltando ou com nome
    desconhecido, ValueError, para o gráfico não sair com uma fatia a menos.

    Ex.: vab_setores_do_estado(linha)["vab_setores_2021"]["servicos"] == 32_580_000_000.0
    """
    setores: dict[str, float] = {}
    for coluna_nome, coluna_valor, coluna_unidade in _COLUNAS_DOS_SETORES:
        chave = _chave_do_setor(linha.get(coluna_nome))
        if chave is None or linha.get(coluna_valor) is None:
            continue
        setores[chave] = valor_absoluto_do_estado(linha[coluna_valor], linha.get(coluna_unidade))
    if len(setores) != len(_CHAVE_POR_SETOR):
        raise ValueError(
            f"VAB por setor do estado incompleto: achei {sorted(setores)}; esperava "
            f"{sorted(_CHAVE_POR_SETOR.values())} em uf_setor2021_maior1..3 e uf_setor2021_menor."
        )

    return {"vab_setores_2021": setores}


def _paises(linha: dict, comercio: str, quantos: int) -> list[tuple[str, object]]:
    nomes = linha.get(f"uf_{comercio}_pais_nome") or []
    valores = linha.get(f"uf_{comercio}_pais_fob") or []

    return list(zip(nomes, valores))[:quantos]


def importacao_paises_do_estado(linha: dict) -> dict[str, object]:
    """`importacao_paises` do municipal: os 10 maiores, das listas da matview (já em
    US$ e em ordem de valor, no mesmo mês citado no texto).

    Ex.: importacao_paises_do_estado(linha)["importacao_paises"][0] == ("China", Decimal("11021478.00"))
    """
    return {"importacao_paises": _paises(linha, "importacao", _PAISES_NA_IMPORTACAO)}


def exportacao_paises_do_estado(linha: dict) -> dict[str, object]:
    """`exportacao_paises` do municipal: os 4 maiores, como no municipal.

    Ex.: exportacao_paises_do_estado(linha)["exportacao_paises"][0] == ("Argentina", Decimal("1397652.00"))
    """
    return {"exportacao_paises": _paises(linha, "exportacao", _PAISES_NA_EXPORTACAO)}


def balanca_do_estado(linha: dict) -> dict[str, object]:
    """`balanca_mensal` e os dois FOB do último mês, como no municipal. Os saldos vêm
    de `uf_balanca_saldo_mensal_01` … `_12` (US$); mês sem dado fica de fora. Os FOB
    só servem à checagem de comércio nos dois sentidos, então a escala não importa.

    Ex.: balanca_do_estado(linha)["balanca_mensal"][0] == ("Jan", Decimal("-38248761.00"))
    """
    meses = enumerate(_ABREVIACOES_DOS_MESES, start=1)
    saldos = [(nome, linha.get(f"uf_balanca_saldo_mensal_{numero:02d}")) for numero, nome in meses]

    return {
        "balanca_mensal": [(nome, saldo) for nome, saldo in saldos if saldo is not None],
        "fob_exportado_ultimo": linha.get("uf_fob_exportado_ultimo"),
        "fob_importado_ultimo": linha.get("uf_fob_importado_ultimo"),
    }
