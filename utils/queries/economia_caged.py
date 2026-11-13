"""Emprego formal (Novo Caged) do relatório de Economia e Renda.

Lê `relatorios_auto.mv_caged_municipal` (db/2026-11-12-mv_caged_municipal.sql): uma
linha por município, já com os marcadores do Doc como colunas, calculados sobre o
último trimestre fechado nos dados. A agregação do microdado leva minutos, por isso
a matview (refresh noturno em scripts/refresh_matviews.sh) e nenhuma conta aqui.
Decisões e razões: Documentacao-OCA, HANDOFF-CAGED-ECONOMIA.md.
"""

import csv
from functools import cache
from pathlib import Path

from utils.queries.base import executar_query_dict

# Identificação já chega ao contexto pela view de perfil; sobrescrever o nm_mun
# canonicalizado em services/generation.py quebraria os joins seguintes.
_COLUNAS_IDENTIFICACAO = ("cd_mun", "nm_mun", "sigla_uf")

# Lista oficial da CBO 2002 (MTE, "Estrutura CBO (CSV)", baixada em 13/11/2026). A base
# do CAGED grava os títulos sem acento ("Alimentador de Linha de Producao") e com
# marcas de cadastro ("Faxineiro (Desativado em 2010)"); o título oficial entra no lugar.
_CBO_CSV = Path(__file__).resolve().parent.parent / "data" / "cbo2002_ocupacao.csv"


@cache
def _titulos_cbo() -> dict[str, str]:
    with _CBO_CSV.open(encoding="utf-8", newline="") as arquivo:
        # " ".join(split()): 41 títulos da lista oficial têm espaço duplo
        # ("Cortador de calçados, a  máquina"), que saía igual no relatório.
        return {
            linha["CODIGO"]: " ".join(linha["TITULO"].split())
            for linha in csv.DictReader(arquivo, delimiter=";")
        }


def _ocupacoes_com_titulo_oficial(linha: dict) -> dict:
    """ocupacao_maior_saldoN pelo título oficial do código (ocupacao_maior_saldoN_cbo),
    com a inicial minúscula porque o Doc cita no meio da frase. Código fora da lista
    oficial (ocupação criada depois, como "massoterapeuta") fica com o nome da base,
    que a matview já entrega em minúsculas."""
    titulos = _titulos_cbo()
    corrigida = dict(linha)
    for posicao in range(1, 5):
        titulo = titulos.get(linha.get(f"ocupacao_maior_saldo{posicao}_cbo") or "")
        if titulo:
            corrigida[f"ocupacao_maior_saldo{posicao}"] = titulo[:1].lower() + titulo[1:]
    return corrigida


_MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
_FIM_DO_TRIMESTRE = {"março": 3, "junho": 6, "setembro": 9, "dezembro": 12}


def _serie_mensal(linha: dict) -> list[tuple[str, object, object]]:
    """(mês, saldo no ano anterior, saldo no ano atual) de janeiro até o último mês
    do trimestre de referência — o recorte da Figura X3. O fim vem de
    `ultimo_mes_tri`, não do primeiro NULL: mês sem nenhuma movimentação também é
    NULL na matview (soma de nada) e cortava a série no meio (Milagres do Maranhão,
    sem movimentação em 2026, ficava sem gráfico). NULL dentro da série é saldo 0."""
    meses = _FIM_DO_TRIMESTRE.get(linha.get("ultimo_mes_tri"), 0)
    return [
        (
            mes,
            linha.get(f"saldo_mes{numero:02d}_ano_anterior") or 0,
            linha.get(f"saldo_mes{numero:02d}_ano_atual") or 0,
        )
        for numero, mes in enumerate(_MESES[:meses], start=1)
    ]


def buscar_caged_municipal(nome_municipio: str, sigla_uf: str) -> dict | None:
    """Marcadores CAGED do município (`economia.$saldo_tri_atual` etc.) mais
    `caged_serie_mensal` para o gráfico. None sem banco ou sem a linha."""
    if not nome_municipio or not sigla_uf:
        return None

    # Mesmo casamento de relatorios_auto.mv_perfil_* (utils/queries/perfil_municipal.py):
    # compara sem o "(UF)" final dos dois lados, porque o nome chega canonicalizado
    # como "Cidade (UF)" e a matview guarda só o nome.
    query = """
        SET LOCAL statement_timeout = '30s';
        SELECT *
        FROM relatorios_auto.mv_caged_municipal
        WHERE LOWER(regexp_replace(nm_mun, '\\s*\\([^)]*\\)\\s*$', '')) =
              LOWER(regexp_replace(%s, '\\s*\\([^)]*\\)\\s*$', ''))
          AND sigla_uf = %s
        LIMIT 1
    """
    params = (nome_municipio, sigla_uf)
    linha = executar_query_dict(query, params, f"CAGED de '{nome_municipio} ({sigla_uf})'")
    if not linha:
        return None
    # Escolaridade e ocupações ficam numa matview à parte (db/2026-11-13-
    # mv_caged_municipal_detalhe.sql): somadas à principal, o refresh passava de 10 min.
    # Sem ela, o parágrafo some pelas condições do Doc (campos ausentes valem 0).
    detalhe = executar_query_dict(
        query.replace("mv_caged_municipal", "mv_caged_municipal_detalhe"),
        params,
        f"CAGED (escolaridade/ocupação) de '{nome_municipio} ({sigla_uf})'",
    )

    marcadores = {
        coluna: valor
        for coluna, valor in {**linha, **_ocupacoes_com_titulo_oficial(detalhe or {})}.items()
        if coluna not in _COLUNAS_IDENTIFICACAO
    }
    marcadores["caged_serie_mensal"] = _serie_mensal(linha)
    return marcadores
