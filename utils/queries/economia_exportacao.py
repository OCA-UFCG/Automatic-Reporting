from utils.queries.perfil_municipal import buscar_perfil_municipal

_UNIDADE_MULTIPLICADOR = {
    "bilhões": 1_000_000_000,
    "milhões": 1_000_000,
    "mil": 1_000,
}

_MESES_BALANCA = ("jan", "fev", "mar", "abr", "mai", "jun")
_NOMES_MESES_BALANCA = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun")

_CAMPOS_MERGE_DIRETOS = (
    "fob_exportado",
    "fob_exportado_unid",
    "kg_exportado",
    "kg_exportado_unid",
    "secao_exportacao1",
    "valor_exportacao_secao1",
    "valor_exportacao_secao1unid",
    "produto_exportado1",
    "valor_exportacao_produto1",
    "valor_exportacao_produto1unid",
    "analise_balanca2",
    "pais_exportacao6destino",
)

# doc usa "balança" (com cedilha); coluna do banco é "balanca" (sem cedilha)
_ALIASES_BALANCA_CEDILHA = {
    "analise_balanca1": "analise_balança1",
    "valor_balanca1": "valor_balança1",
    "valor_balanca1unid": "valor_balança1unid",
    "valor_balanca6meses": "valor_balança6meses",
    "valor_balanca6mesesunid": "valor_balança6mesesunid",
}

# doc referencia "fob_exportado_ultimo" (síntese) para o mesmo valor
_ALIASES_FOB_EXPORTADO_ULTIMO = {
    "fob_exportado": "fob_exportado_ultimo",
    "fob_exportado_unid": "fob_exportado_ultimo_unid",
}


def _valor_absoluto(valor: object, unidade: object) -> float | None:
    if valor is None:
        return None
    return float(valor) * _UNIDADE_MULTIPLICADOR.get(unidade, 1)


def buscar_comercio_exterior_economia(
    nome_municipio: str, sigla_uf: str
) -> dict[str, object] | None:
    linha = buscar_perfil_municipal("economia-renda", nome_municipio, sigla_uf)
    if linha is None:
        return None

    dados: dict[str, object] = {
        campo: linha[campo] for campo in _CAMPOS_MERGE_DIRETOS if linha.get(campo) is not None
    }

    for campo_banco, campo_doc in _ALIASES_BALANCA_CEDILHA.items():
        if linha.get(campo_banco) is not None:
            dados[campo_doc] = linha[campo_banco]

    for campo_base, alias in _ALIASES_FOB_EXPORTADO_ULTIMO.items():
        if linha.get(campo_base) is not None:
            dados[alias] = linha[campo_base]

    # doc usa "balanca"/"balanca2" (bare) na síntese final
    if linha.get("analise_balanca1") is not None:
        dados["balanca"] = linha["analise_balanca1"]
    if linha.get("analise_balanca2") is not None:
        dados["balanca2"] = linha["analise_balanca2"]

    paises_exportacao = []
    for posicao in range(1, 5):
        nome_pais = linha.get(f"pais_exportacao{posicao}")
        valor_pais = linha.get(f"valor_pais_exportacao{posicao}")
        unidade_pais = linha.get(f"valor_pais_exportacaounid{posicao}")

        if nome_pais is not None:
            dados[f"pais_exportacao{posicao}"] = nome_pais
        if valor_pais is not None:
            dados[f"valor_pais_exportacao{posicao}"] = valor_pais
        if unidade_pais is not None:
            dados[f"valor_pais_exportacaounid{posicao}"] = unidade_pais

        if nome_pais is not None and valor_pais is not None:
            paises_exportacao.append(
                (nome_pais, _valor_absoluto(valor_pais, unidade_pais))
            )

    # doc usa "exportacao1/2/3" (sem "pais_") pro nome do país nesta seção
    for posicao in (1, 2, 3):
        if f"pais_exportacao{posicao}" in dados:
            dados[f"exportacao{posicao}"] = dados[f"pais_exportacao{posicao}"]

    if paises_exportacao:
        dados["exportacao_paises"] = paises_exportacao

    balanca_mensal = [
        (nome_mes, float(linha[f"valor_balanca_{mes}"]))
        for mes, nome_mes in zip(_MESES_BALANCA, _NOMES_MESES_BALANCA)
        if linha.get(f"valor_balanca_{mes}") is not None
    ]
    if balanca_mensal:
        dados["balanca_mensal"] = balanca_mensal

    return dados
