from collections import defaultdict

from utils.queries.base import escalar_valor, executar_query

DADOS_IMPORTACAO_MUNICIPAL = """
    SELECT
        co_ano,
        co_mes,
        desc_mes,
        desc_pais_portugues,
        desc_secao,
        desc_sh4,
        kg_liquido,
        vl_fob
    FROM eco_importacao.vw_importacao_completa
    WHERE LOWER(nm_mun) = LOWER(%s)
      AND sigla_uf = %s
      AND co_ano = (
          SELECT MAX(co_ano)
          FROM eco_importacao.vw_importacao_completa
          WHERE LOWER(nm_mun) = LOWER(%s)
            AND sigla_uf = %s
      )
    ORDER BY co_mes::int
"""

_COLUNAS_LINHA_IMPORTACAO = (
    "co_ano",
    "co_mes",
    "desc_mes",
    "desc_pais_portugues",
    "desc_secao",
    "desc_sh4",
    "kg_liquido",
    "vl_fob",
)


def buscar_linhas_importacao(nome_municipio: str, sigla_uf: str) -> list[dict]:
    """Busca, em uma única consulta, as importações do último ano disponível.

    O último ano é resolvido dentro do próprio SQL (subquery MAX(co_ano)) para
    não trazer o histórico completo do município — só o necessário para o
    resumo do último mês e a comparação janeiro x junho usados no texto.
    """
    linhas = executar_query(
        DADOS_IMPORTACAO_MUNICIPAL,
        (nome_municipio, sigla_uf, nome_municipio, sigla_uf),
        f"dados de importação de '{nome_municipio} ({sigla_uf})'",
        buscar_todas=True,
    )
    if not linhas:
        return []
    return [dict(zip(_COLUNAS_LINHA_IMPORTACAO, linha)) for linha in linhas]


def _somar_por_chave(linhas: list[dict], chave: str, campo_valor: str) -> dict[str, float]:
    totais: dict[str, float] = defaultdict(float)
    for linha in linhas:
        nome = linha.get(chave)
        valor = linha.get(campo_valor)
        if nome is None or valor is None:
            continue
        totais[nome] += float(valor)
    return dict(totais)


def _top_n(totais: dict[str, float], top: int) -> list[tuple[str, float]]:
    return sorted(totais.items(), key=lambda item: item[1], reverse=True)[:top]


def _valor_medio_por_kg(linhas: list[dict]) -> float | None:
    fob_total = sum(
        float(linha["vl_fob"]) for linha in linhas if linha.get("vl_fob") is not None
    )
    kg_total = sum(
        float(linha["kg_liquido"]) for linha in linhas if linha.get("kg_liquido") is not None
    )
    if not kg_total:
        return None
    return fob_total / kg_total


def processar_importacao(linhas: list[dict]) -> dict[str, object] | None:
    if not linhas:
        return None

    ultima_linha = max(linhas, key=lambda linha: (linha["co_ano"], int(linha["co_mes"])))
    ultimo_ano = ultima_linha["co_ano"]
    ultimo_mes = ultima_linha["co_mes"]
    linhas_ultimo_mes = [
        linha
        for linha in linhas
        if linha["co_ano"] == ultimo_ano and linha["co_mes"] == ultimo_mes
    ]

    fob_ultimo = sum(
        float(linha["vl_fob"]) for linha in linhas_ultimo_mes if linha.get("vl_fob") is not None
    )
    kg_ultimo = sum(
        float(linha["kg_liquido"])
        for linha in linhas_ultimo_mes
        if linha.get("kg_liquido") is not None
    )

    resultado: dict[str, object] = {
        "ultimo_mes_ano": f"{ultima_linha['desc_mes']} de {ultimo_ano}",
        "ultimo_jun": ultimo_ano,
    }

    fob_valor, fob_unid = escalar_valor(fob_ultimo)
    kg_valor, kg_unid = escalar_valor(kg_ultimo)
    resultado["fob_importado_ultimo"] = fob_valor
    resultado["fob_importado_ultimo_unid"] = fob_unid
    resultado["kg_importado_ultimo"] = kg_valor
    resultado["kg_importado_ultimo_unid"] = kg_unid

    # pais_importado{1-4}: os 4 principais países de origem das importações
    # do último mês, por valor FOB.
    totais_pais = _somar_por_chave(linhas_ultimo_mes, "desc_pais_portugues", "vl_fob")
    for posicao, (nome_pais, valor_fob) in enumerate(_top_n(totais_pais, 4), start=1):
        valor_escalado, unidade = escalar_valor(valor_fob)
        resultado[f"pais_importado{posicao}"] = nome_pais
        resultado[f"valor_pais_importado{posicao}"] = valor_escalado
        resultado[f"valor_pais_importado_unid{posicao}"] = unidade

    # secao_produtos{1-2}: as 2 seções (categorias amplas de produto) de
    # maior valor FOB importado no último mês.
    totais_secao = _somar_por_chave(linhas_ultimo_mes, "desc_secao", "vl_fob")
    for posicao, (nome_secao, valor_fob) in enumerate(_top_n(totais_secao, 2), start=1):
        valor_escalado, unidade = escalar_valor(valor_fob)
        resultado[f"secao_produtos{posicao}"] = nome_secao
        resultado[f"valor_secao_importado{posicao}"] = valor_escalado
        resultado[f"valor_secao_importado_unid{posicao}"] = unidade

    # produto_importado{1-2}: os 2 produtos (SH4) de maior valor FOB
    # importado no último mês, com o respectivo volume em kg. O Doc repete o
    # nome do produto em "produto_importado_kg1"/"produto_importadokg2" na
    # frase sobre volume físico.
    totais_produto_fob = _somar_por_chave(linhas_ultimo_mes, "desc_sh4", "vl_fob")
    totais_produto_kg = _somar_por_chave(linhas_ultimo_mes, "desc_sh4", "kg_liquido")
    top_produtos = _top_n(totais_produto_fob, 2)
    for posicao, (nome_produto, valor_fob) in enumerate(top_produtos, start=1):
        valor_escalado, unidade = escalar_valor(valor_fob)
        resultado[f"produto_importado{posicao}"] = nome_produto
        resultado[f"valor_produto_importado{posicao}"] = valor_escalado
        resultado[f"valor_produto_importadounid{posicao}"] = unidade

        kg_escalado, kg_unidade = escalar_valor(totais_produto_kg.get(nome_produto))
        resultado[f"kg_importado_produto{posicao}"] = kg_escalado
        resultado[f"kg_importado_produtounid{posicao}"] = kg_unidade

    if len(top_produtos) >= 1:
        resultado["produto_importado_kg1"] = top_produtos[0][0]
    if len(top_produtos) >= 2:
        resultado["produto_importadokg2"] = top_produtos[1][0]

    # Comparação do valor médio por kg entre janeiro e junho do ano corrente
    # ("$valormedio_importado_jan" / "$valormedio_importado_jun" no texto).
    linhas_jan = [
        linha
        for linha in linhas
        if linha["co_ano"] == ultimo_ano and int(linha["co_mes"]) == 1
    ]
    linhas_jun = [
        linha
        for linha in linhas
        if linha["co_ano"] == ultimo_ano and int(linha["co_mes"]) == 6
    ]
    valormedio_jan = _valor_medio_por_kg(linhas_jan)
    valormedio_jun = _valor_medio_por_kg(linhas_jun)
    if valormedio_jan is not None:
        valor, unidade = escalar_valor(valormedio_jan)
        resultado["valormedio_importado_jan"] = valor
        resultado["valormedio_importado_janunid"] = unidade
    if valormedio_jun is not None:
        valor, unidade = escalar_valor(valormedio_jun)
        resultado["valormedio_importado_jun"] = valor
        resultado["valormedio_importado_jununid"] = unidade
    if valormedio_jan is not None and valormedio_jun is not None:
        resultado["analise_importado_janjun"] = (
            "aumento" if valormedio_jun >= valormedio_jan else "redução"
        )

    return resultado
