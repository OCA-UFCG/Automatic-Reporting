from collections import defaultdict

from utils.queries.base import (
    escalar_valor_por_extenso,
    executar_query,
    unidade_de_massa,
)

# eco_importacao.vw_importacao_completa parou de ser atualizado pela equipe de
# dados (ficou parado em julho/2026); eco_comercio_exterior.impexp_completa é o
# schema novo, com importação e exportação na mesma tabela (`tipo_operacao`).
# mv_perfil_economia já usa esse schema novo para os totais; esta query cobre
# o detalhamento por país/produto/seção que a matview não tem.
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
    FROM eco_comercio_exterior.impexp_completa
    WHERE tipo_operacao = 'Importação'
      AND LOWER(desc_municipio) = LOWER(%s)
      AND sg_uf_mun = %s
      AND co_ano = (
          SELECT MAX(co_ano)
          FROM eco_comercio_exterior.impexp_completa
          WHERE tipo_operacao = 'Importação'
            AND LOWER(desc_municipio) = LOWER(%s)
            AND sg_uf_mun = %s
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

    # O banco guarda desc_mes/desc_secao/desc_sh4 capitalizados e o Doc usa todos
    # no meio da frase ("destacaram-se $secao_importado1, com..."), por isso o
    # .lower() aqui e nas seções/produtos abaixo.
    resultado: dict[str, object] = {
        "ultimo_mes_ano": f"{ultima_linha['desc_mes'].lower()} de {ultimo_ano}",
        "ultimo_jun": ultimo_ano,
    }

    fob_valor, fob_unid = escalar_valor_por_extenso(fob_ultimo)
    kg_valor, kg_unid = escalar_valor_por_extenso(kg_ultimo)
    resultado["fob_importado_ultimo"] = fob_valor
    resultado["fob_importado_ultimo_unid"] = fob_unid
    resultado["kg_importado_ultimo"] = kg_valor
    resultado["kg_importado_ultimo_unid"] = unidade_de_massa(kg_unid)

    totais_pais = _somar_por_chave(linhas_ultimo_mes, "desc_pais_portugues", "vl_fob")
    top10_paises = _top_n(totais_pais, 10)
    resultado["importacao_paises"] = top10_paises
    for posicao, (nome_pais, valor_fob) in enumerate(top10_paises[:4], start=1):
        valor_escalado, unidade = escalar_valor_por_extenso(valor_fob)
        resultado[f"pais_importado{posicao}"] = nome_pais
        resultado[f"valor_pais_importado{posicao}"] = valor_escalado
        resultado[f"valor_pais_importado_unid{posicao}"] = unidade

    totais_secao = _somar_por_chave(linhas_ultimo_mes, "desc_secao", "vl_fob")
    for posicao, (nome_secao, valor_fob) in enumerate(_top_n(totais_secao, 2), start=1):
        valor_escalado, unidade = escalar_valor_por_extenso(valor_fob)
        resultado[f"secao_importado{posicao}"] = nome_secao.lower()
        resultado[f"valor_secao_importado{posicao}"] = valor_escalado
        resultado[f"valor_secao_importado_unid{posicao}"] = unidade

    totais_produto_fob = _somar_por_chave(linhas_ultimo_mes, "desc_sh4", "vl_fob")
    totais_produto_kg = _somar_por_chave(linhas_ultimo_mes, "desc_sh4", "kg_liquido")
    top_produtos = _top_n(totais_produto_fob, 2)
    for posicao, (nome_produto, valor_fob) in enumerate(top_produtos, start=1):
        valor_escalado, unidade = escalar_valor_por_extenso(valor_fob)
        resultado[f"produto_importado{posicao}"] = nome_produto.lower()
        resultado[f"valor_produto_importado{posicao}"] = valor_escalado
        resultado[f"valor_produto_importadounid{posicao}"] = unidade

    # "Quanto ao peso, sobressaíram-se…" lista os mais pesados, como a view faz;
    # não o peso dos dois de maior valor.
    top_produtos_kg = _top_n(totais_produto_kg, 2)
    # "O único produto… correspondentes a $kg_importado_produto1 kg": o peso é o dele.
    if len(top_produtos) < 2:
        top_produtos_kg = [
            (nome_produto, totais_produto_kg.get(nome_produto))
            for nome_produto, _valor_fob in top_produtos
        ]
    # Menos de dois produtos com peso: completa com o próximo por valor (0 kg no
    # default abaixo), para não sobrar nome de produto vazio.
    for nome_produto, _valor_fob in top_produtos:
        if len(top_produtos_kg) >= 2:
            break
        if nome_produto not in dict(top_produtos_kg):
            top_produtos_kg.append((nome_produto, None))
    for posicao, (nome_produto, kg_produto) in enumerate(top_produtos_kg, start=1):
        resultado[f"produto_importado_kg{posicao}"] = nome_produto.lower()
        # Sem peso, escalar devolve None: gravar deixaria $kg cru; cai no default 0.
        kg_escalado, kg_unidade = escalar_valor_por_extenso(kg_produto)
        if kg_escalado is not None:
            resultado[f"kg_importado_produto{posicao}"] = kg_escalado
            resultado[f"kg_importado_produtounid{posicao}"] = unidade_de_massa(kg_unidade)

    # generation.py mescla este dict por cima da linha da mv_perfil_economia, que
    # traz estes mesmos campos de outro recorte: slot não preenchido aqui deixaria
    # o valor da view aparecer ao lado dos nossos (foi assim que a soma dos quatro
    # países passou do total importado).
    for posicao in range(1, 5):
        resultado.setdefault(f"pais_importado{posicao}", "")
        resultado.setdefault(f"valor_pais_importado{posicao}", 0)
        resultado.setdefault(f"valor_pais_importado_unid{posicao}", "")
    for posicao in (1, 2):
        resultado.setdefault(f"secao_importado{posicao}", "")
        resultado.setdefault(f"valor_secao_importado{posicao}", 0)
        resultado.setdefault(f"valor_secao_importado_unid{posicao}", "")
        resultado.setdefault(f"produto_importado{posicao}", "")
        resultado.setdefault(f"valor_produto_importado{posicao}", 0)
        resultado.setdefault(f"valor_produto_importadounid{posicao}", "")
        resultado.setdefault(f"kg_importado_produto{posicao}", 0)
        resultado.setdefault(f"kg_importado_produtounid{posicao}", "")
        resultado.setdefault(f"produto_importado_kg{posicao}", "")

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
        valor, unidade = escalar_valor_por_extenso(valormedio_jan)
        resultado["valormedio_importado_jan"] = valor
        resultado["valormedio_importado_janunid"] = unidade
    if valormedio_jun is not None:
        valor, unidade = escalar_valor_por_extenso(valormedio_jun)
        resultado["valormedio_importado_jun"] = valor
        resultado["valormedio_importado_jununid"] = unidade
    if valormedio_jan is not None and valormedio_jun is not None:
        resultado["analise_importado_janjun"] = (
            "aumento" if valormedio_jun >= valormedio_jan else "redução"
        )

    return resultado
