import re


def _resolver_caminho_em_contexto(contexto: dict, caminho: str) -> object | None:
    atual: object = contexto
    for parte in caminho.split("."):
        if not isinstance(atual, dict) or parte not in atual:
            return None
        atual = atual[parte]
    return atual


def _resolver_campo_com_alias(contexto: dict, campo: str) -> object | None:
    valor = _resolver_caminho_em_contexto(contexto, campo)
    if valor is not None:
        return valor

    aliases_de_coluna = {
        "fundamental_com_per": "fundamental_comp_per",
        "comparar_analfabetismo_idade": "analfabetismo_jovens_idosos",
        "raca_maior": "cor_maior",
        "raca_menor": "cor_menor",
    }
    campo_original = aliases_de_coluna.get(campo)
    if campo_original:
        valor = _resolver_caminho_em_contexto(contexto, campo_original)
        if valor is not None:
            return valor

    if campo == "city":
        return _resolver_caminho_em_contexto(contexto, "nm_mun")

    if campo == "municipio":
        return _resolver_caminho_em_contexto(contexto, "nm_mun")

    if campo == "year":
        return _resolver_caminho_em_contexto(contexto, "ano")

    if campo == "ano":
        return _resolver_caminho_em_contexto(contexto, "year")

    return None


def _resolver_contexto_por_alias(contexto: dict, alias: str, namespace: str) -> dict:
    if alias == namespace.lower():
        return contexto

    valor_alias = contexto.get(alias)
    if isinstance(valor_alias, dict):
        return valor_alias

    return contexto


def substituir_placeholders(texto: str, contexto: dict, namespace: str = "demografia") -> str:
    alias_de_tabela = {
        "table": _resolver_contexto_por_alias(contexto, "table", namespace),
        "tabela": _resolver_contexto_por_alias(contexto, "tabela", namespace),
        "sheet": _resolver_contexto_por_alias(contexto, "sheet", namespace),
        "planilha": _resolver_contexto_por_alias(contexto, "planilha", namespace),
        "linha": contexto,
        "dados": contexto,
        "csv": contexto,
    }

    def _substituir_dolar(match: re.Match) -> str:
        placeholder_namespace = match.group(1).lower()
        campo = match.group(2)

        if placeholder_namespace == namespace.lower():
            contexto_alvo = contexto
        else:
            contexto_alvo = alias_de_tabela.get(placeholder_namespace)

        if isinstance(contexto_alvo, dict):
            valor = _resolver_campo_com_alias(contexto_alvo, campo)
            if valor is not None:
                return str(valor)
        return match.group(0)

    alias_map = {
        "city": contexto.get("nm_mun", ""),
        "year": contexto.get("ano", ""),
        "municipio": contexto.get("nm_mun", ""),
        "ano": contexto.get("ano", ""),
        "data_relatorio": contexto.get("data_relatorio", ""),
        "hora_relatorio": contexto.get("hora_relatorio", ""),
        "data_geracao": contexto.get("data_relatorio", ""),
        "hora_geracao": contexto.get("hora_relatorio", ""),
    }

    resultado = texto

    # Formato completo: macrotema.nome_do_csv.$campo.
    resultado = re.sub(
        rf"(?i)(?<![\w]){re.escape(namespace)}\."
        rf"{re.escape(namespace)}\.\$([A-Za-z_][\w]*)",
        lambda m: str(
            _resolver_campo_com_alias(contexto, m.group(1))
            if _resolver_campo_com_alias(contexto, m.group(1)) is not None
            else m.group(0)
        ),
        resultado,
    )

    # Formato usado em alguns documentos: namespace.$campo.
    resultado = re.sub(
        rf"(?i)(?<![\w]){re.escape(namespace)}\.\$([A-Za-z_][\w]*)",
        lambda m: str(
            _resolver_campo_com_alias(contexto, m.group(1))
            if _resolver_campo_com_alias(contexto, m.group(1)) is not None
            else m.group(0)
        ),
        resultado,
    )

    # Formato usado nos documentos: $Table.nome_da_tabela$campo.
    resultado = re.sub(
        r"\$(?:table|tabela|sheet|planilha)\.[A-Za-z_][\w]*\$([A-Za-z_][\w]*)",
        lambda m: str(
            _resolver_campo_com_alias(contexto, m.group(1))
            if _resolver_campo_com_alias(contexto, m.group(1)) is not None
            else m.group(0)
        ),
        resultado,
        flags=re.IGNORECASE,
    )

    resultado = re.sub(
        r"\$([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)",
        _substituir_dolar,
        resultado,
    )

    # Campos simples vêm diretamente da linha da tabela do macrotema.
    resultado = re.sub(
        r"\$([A-Za-z_][\w]*)",
        lambda m: str(
            _resolver_campo_com_alias(contexto, m.group(1))
            if _resolver_campo_com_alias(contexto, m.group(1)) is not None
            else m.group(0)
        ),
        resultado,
    )

    for alias, valor in alias_map.items():
        resultado = resultado.replace(f"${alias}", str(valor))

    resultado = re.sub(
        r'\{\{\s*(\w+)\s*\}\}',
        lambda m: str(contexto.get(m.group(1), m.group(0))),
        resultado,
    )

    return resultado
