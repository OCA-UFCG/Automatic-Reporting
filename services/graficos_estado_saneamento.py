"""Adaptadores dos gráficos de Infraestrutura e Saneamento no relatório por estado
(12/11/2026). Mesma ideia de services/graficos_estado.py: montar, a partir da linha
`uf_*` da est_infraestrutura, o que as funções de plotting/saneamento.py já leem.

A dinâmica do esgoto (2000, 2010, 2022) e a coleta de lixo (2010, 2022) têm os
mesmos anos do municipal e vêm da matview.

A rosca de tipos de esgotamento precisa das 7 categorias, e a matview não tem
fossa séptica nem "sem banheiro" (I6 do registro): uf_distrib_esgoto_2022_completa
vale 0 nos 9 estados, e o Doc estadual escreve, nesse caso, que a distribuição não
está completa. Decisão de 12/11/2026: seguir essa flag. Com ela em 1, as 7
categorias vêm somadas por estado da view do painel; com ela em 0, a rosca não sai
e nem a consulta roda.
"""

from utils.queries.saneamento import (
    CATEGORIAS_ESGOTAMENTO,
    buscar_esgotamento_sanitario_estado,
)

_FLAG_DISTRIBUICAO_COMPLETA = "uf_distrib_esgoto_2022_completa"
_CHAVES_DA_ROSCA = ("esg_total", *(chave for chave, _ in CATEGORIAS_ESGOTAMENTO))


def _sem_prefixo(linha: dict, chaves: tuple[str, ...]) -> dict[str, object]:
    return {chave: linha.get(f"uf_{chave}") for chave in chaves}


def dinamica_esgoto_do_estado(linha: dict) -> dict[str, object]:
    """`esgoto_rede_<ano>` do municipal (2000, 2010 e 2022), lidas de `uf_esgoto_rede_<ano>`.

    Ex.: dinamica_esgoto_do_estado(linha)["esgoto_rede_2022"] == Decimal("46.80")
    """
    return _sem_prefixo(linha, ("esgoto_rede_2000", "esgoto_rede_2010", "esgoto_rede_2022"))


def coleta_lixo_do_estado(linha: dict) -> dict[str, object]:
    """`coleta_<ano>` do municipal (2010 e 2022), lidas de `uf_coleta_<ano>`.

    Ex.: coleta_lixo_do_estado(linha)["coleta_2022"] == Decimal("84.61")
    """
    return _sem_prefixo(linha, ("coleta_2010", "coleta_2022"))


def distribuicao_completa(linha: dict) -> bool:
    """A flag da matview que o Doc usa para escolher entre o texto da distribuição
    completa e o da incompleta."""
    return linha.get(_FLAG_DISTRIBUICAO_COMPLETA) == 1


def complemento_de_saneamento(linha: dict) -> dict[str, object]:
    """As 7 categorias da rosca somadas do painel, só com a flag em 1; senão {}, sem
    consultar o banco.

    Ex.: complemento_de_saneamento({"uf_sigla_uf": "PB", "uf_distrib_esgoto_2022_completa": 0}) == {}
    """
    if not distribuicao_completa(linha):
        return {}

    return buscar_esgotamento_sanitario_estado(str(linha.get("uf_sigla_uf") or "")) or {}


def esgotamento_do_estado(linha: dict) -> dict[str, object]:
    """`esg_total` e as 7 categorias do municipal, vindas do complemento. Com a flag
    em 0, ValueError: a rosca fica de fora e o texto do Doc continua coerente.

    Ex.: esgotamento_do_estado(linha_com_flag_1)["esg_fossa_septica_ou_fossa_filtro"] == 251638
    """
    if not distribuicao_completa(linha):
        raise ValueError(
            f"Distribuição do esgotamento incompleta na matview "
            f"({_FLAG_DISTRIBUICAO_COMPLETA}={linha.get(_FLAG_DISTRIBUICAO_COMPLETA)!r}); "
            "esperava 1 para gerar a rosca."
        )

    return {chave: linha.get(chave) for chave in _CHAVES_DA_ROSCA}
