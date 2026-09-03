from utils.formatting import categoria_variacao as _categoria_variacao
from utils.queries.base import executar_query

PERFIL_DESENVOLVIMENTO_SOCIAL_MUNICIPAL = """
    SELECT
        idhm_1991,
        idhm_2000,
        idhm_2010,
        idhm_classe_2010,
        nomesubindice1_2010,
        subindice1_2010,
        nomesubindice2_2010,
        subindice2_2010,
        nomesubindice3_2010,
        subindice3_2010,
        analise1_idhm,
        var_idhm_per_1991_2010,
        gini_2010,
        renda_2010,
        bolsa_familia_per_2013,
        analise2_idhm,
        analise_gini_2010
    FROM relatorios_auto.vw_perfil_desen_social_municipal
    WHERE nm_mun = %s
      AND sigla_uf = %s
"""


def _categoria_variacao(variacao) -> str | None:
    if variacao is None:
        return None
    try:
        valor = float(variacao)
    except (TypeError, ValueError):
        return None
    if valor > 0:
        return "um aumento"
    if valor < 0:
        return "uma diminuição"
    return "uma estabilidade"


def buscar_perfil_desenvolvimento_social(
    nome_municipio: str, sigla_uf: str
) -> dict[str, object] | None:
    linha = executar_query(
        PERFIL_DESENVOLVIMENTO_SOCIAL_MUNICIPAL,
        (nome_municipio, sigla_uf),
        f"perfil de desenvolvimento social de '{nome_municipio} ({sigla_uf})'",
    )
    if linha is None:
        return None

    (
        idhm_1991,
        idhm_2000,
        idhm_2010,
        idhm_classe_2010,
        nomesubindice1_2010,
        subindice1_2010,
        nomesubindice2_2010,
        subindice2_2010,
        nomesubindice3_2010,
        subindice3_2010,
        analise1_idhm,
        var_idhm_per_1991_2010,
        gini_2010,
        renda_2010,
        bolsa_familia_per_2013,
        analise2_idhm,
        analise_gini_2010,
    ) = linha

    var_idhm_1991_2010 = None
    if idhm_1991 is not None and idhm_2010 is not None:
        try:
            var_idhm_1991_2010 = round(float(idhm_2010) - float(idhm_1991), 3)
        except (TypeError, ValueError):
            var_idhm_1991_2010 = None

    dados = {
        "idhm_1991": idhm_1991,
        "idhm_2000": idhm_2000,
        "idhm_2010": idhm_2010,
        "idhm_classe_2010": idhm_classe_2010,
        "nomesubindice1_2010": nomesubindice1_2010,
        "subindice1_2010": subindice1_2010,
        "nomesubindice2_2010": nomesubindice2_2010,
        "subindice2_2010": subindice2_2010,
        "nomesubindice3_2010": nomesubindice3_2010,
        "subindice3_2010": subindice3_2010,
        "analise1_idhm": analise1_idhm,
        "var_idhm_per_1991_2010": var_idhm_per_1991_2010,
        "var_idhm_1991_2010": var_idhm_1991_2010,
        "cat_idhm_1991_2010": _categoria_variacao(var_idhm_1991_2010),
        "gini_2010": gini_2010,
        "renda_2010": renda_2010,
        "bolsa_familia_per_2013": bolsa_familia_per_2013,
        "analise2_idhm": analise2_idhm,
        "analise_gini_2010": analise_gini_2010,
    }
    return {campo: valor for campo, valor in dados.items() if valor is not None}
