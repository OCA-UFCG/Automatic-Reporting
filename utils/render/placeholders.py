import re
from decimal import Decimal

from utils.formatting import formatar_numero_ptbr

_MARCADOR_CAMPO_CONDICIONAL = re.compile(r"(?:[A-Za-z_][\w-]*\.)?\$([A-Za-z_][\w]*)")


def _avaliar_condicao_editorial(
    matches: list[re.Match], expressao: str, contexto: dict
) -> bool:
    campos = [match.group(1) for match in matches]

    def numero(campo: str) -> float:
        valor = _resolver_campo_com_alias(contexto, campo)
        try:
            return float(valor or 0)
        except (TypeError, ValueError):
            return 0.0

    valores = [numero(campo) for campo in campos]
    operadores: list[str | None] = []
    for indice, match in enumerate(matches):
        fim = matches[indice + 1].start() if indice + 1 < len(matches) else len(expressao)
        trecho = expressao[match.end():fim].casefold()
        operador = next(
            (op for op in ("maior que 1", "diferente de 0", "igual a 0", "igual a 1") if op in trecho),
            None,
        )
        operadores.append(operador)
    operador_compartilhado = next((op for op in reversed(operadores) if op), None)
    operadores = [op or operador_compartilhado for op in operadores]

    def atende(valor: float, operador: str | None) -> bool:
        if operador == "maior que 1":
            return valor > 1
        if operador == "diferente de 0":
            return valor != 0
        if operador == "igual a 0":
            return valor == 0
        if operador == "igual a 1":
            return valor == 1
        return False

    return all(atende(valor, operador) for valor, operador in zip(valores, operadores))


def interpretar_blocos_condicionais(texto: str, contexto: dict) -> str:
    """Interpreta as instruções editoriais usadas nos documentos demográficos.

    As linhas ``Para quando ...:`` controlam os parágrafos seguintes e não são
    exibidas. Condições de 2010 ficam subordinadas ao bloco indígena/quilombola
    imediatamente anterior.
    """
    resultado: list[str] = []
    bloco_ativo = True
    bloco_populacoes_ativo = True
    bloco_rua_ativo = True

    for linha in texto.splitlines():
        limpa = linha.strip()
        if re.match(r"(?i)^sequ[eê]ncia do texto,?\s*sem condi[cç][aã]o:?$", limpa):
            bloco_ativo = True
            bloco_populacoes_ativo = True
            continue

        condicao = re.match(r"(?i)^para(?:\s+quando)?\s+(.+?):\s*$", limpa)
        if condicao:
            expressao = condicao.group(1)
            matches = list(_MARCADOR_CAMPO_CONDICIONAL.finditer(expressao))
            if matches:
                campos = {match.group(1) for match in matches}
                atende = _avaliar_condicao_editorial(matches, expressao, contexto)
                if campos & {"pop_ind_2022", "pop_qui"}:
                    bloco_populacoes_ativo = atende
                    bloco_ativo = atende
                elif "pop_ind_2010" in campos:
                    bloco_ativo = bloco_populacoes_ativo and atende
                elif campos == {"centro_pop"}:
                    # O Centro POP vem da mesma consulta da população em situação
                    # de rua: sem esses dados, não há como afirmar se o município
                    # tinha ou não um Centro POP.
                    bloco_ativo = bloco_rua_ativo and atende
                else:
                    bloco_ativo = atende
                continue
            # Sem "$campo", não é uma instrução editorial de fato — é uma frase
            # comum do texto (ex.: "Para efeito de análise:") e deve ser mantida.

        if limpa.casefold() in {"síntese", "sintese"}:
            bloco_ativo = True
            bloco_populacoes_ativo = True
            bloco_rua_ativo = True

        # Nos documentos atuais, este parágrafo encerra as condições internas
        # referentes a 2010 e volta ao bloco indígena/quilombola principal.
        if re.match(
            r"^quanto à população (autodeclarad[ao]\s+)?quilombola",
            limpa.casefold(),
        ):
            bloco_ativo = bloco_populacoes_ativo

        # O parágrafo de situação de rua não tem guarda "Para quando ...:" no
        # documento (é declarado como "sem condição"), mas depende de dados que
        # podem não existir para o município. Sem eles, evitamos expor os
        # placeholders crus e usamos um texto equivalente ao das outras seções
        # quando não há registros.
        if re.match(
            r"(?i)^outro grupo relevante para a caracteriza[cç][aã]o da popula[cç][aã]o municipal",
            limpa,
        ):
            bloco_rua_ativo = _resolver_campo_com_alias(contexto, "pop_rua_2022") is not None
            if bloco_ativo and not bloco_rua_ativo:
                nome_mun = _resolver_campo_com_alias(contexto, "nm_mun") or "o município"
                resultado.append(
                    f"Não foram encontrados registros de pessoas em situação de rua "
                    f"para {nome_mun} na fonte de dados consultada. Contudo, esse "
                    "resultado deve ser interpretado considerando os limites da base "
                    "de dados utilizada, não sendo suficiente, por si só, para "
                    "afastar a presença dessa população no município."
                )
                continue

        if bloco_ativo:
            resultado.append(linha)

    return "\n".join(resultado)


def _resolver_caminho_em_contexto(contexto: dict, caminho: str) -> object | None:
    atual: object = contexto
    for parte in caminho.split("."):
        if not isinstance(atual, dict) or parte not in atual:
            return None
        atual = atual[parte]
    return atual


def _resolver_percentual_derivado(contexto: dict, campo: str) -> object | None:
    if not campo.endswith("_per"):
        return None

    campo_base = campo[: -len("_per")]
    valor_base = _resolver_caminho_em_contexto(contexto, campo_base)
    total = _resolver_caminho_em_contexto(contexto, "pop_total")
    if valor_base is None or not total:
        return None

    try:
        return round(float(valor_base) / float(total) * 100, 1)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _resolver_campo_com_alias(contexto: dict, campo: str) -> object | None:
    valor = _resolver_caminho_em_contexto(contexto, campo)
    if valor is not None:
        return valor

    aliases_de_coluna = {
        "area": "area_territorial",
        "centro_pop": "centros_pop",
        "fundamental_com_per": "fundamental_comp_per",
        "comparar_analfabetismo_idade": "analfabetismo_jovens_idosos",
        "pop_ind_2022": "pop_total_indigena",
        "pop_ind_homem_2022": "homem_indigena",
        "pop_ind_mulher_2022": "mulher_indigena",
        "pop_rua_2022": "pop_rua_total",
        "pop_rua_pobreza": "pobreza_cadunico",
        "pop_rua_br": "baixa_renda_cadunico",
        "pop_rua_acima_br": "acima_meio_sm_cadunico",
        "pop_rua_bolsaf_2022": "familias_rua_bf",
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

    if campo == "cres_pop_analise":
        crescimento = _resolver_caminho_em_contexto(contexto, "cres_pop")
        if crescimento is not None:
            try:
                return "crescimento" if float(crescimento) >= 0 else "redução"
            except (TypeError, ValueError):
                pass

    valor = _resolver_percentual_derivado(contexto, campo)
    if valor is not None:
        return valor

    return None


def _formatar_valor(valor: object) -> str:
    if isinstance(valor, bool):
        return str(valor)
    if isinstance(valor, (int, float, Decimal)):
        numero = float(valor)
        decimais = 0 if numero == int(numero) else 1
        return formatar_numero_ptbr(numero, decimais=decimais)
    return str(valor)


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

    def _resolver_ou_manter(match: re.Match) -> str:
        valor = _resolver_campo_com_alias(contexto, match.group(1))
        return _formatar_valor(valor) if valor is not None else match.group(0)

    def _substituir_dolar(match: re.Match) -> str:
        placeholder_namespace = match.group(1).lower()
        campo = match.group(2)

        aliases_namespace = {
            "demografia": {"demografia", "demo"},
            "economia-renda": {"economia-renda", "economia"},
            "hidraulica": {"hidraulica", "seg_hidrica"},
            "saneamento": {"saneamento", "infraestrutura"},
            "meio-ambiente": {"meio-ambiente", "ambiente"},
            "desenvolvimento-social": {"desenvolvimento-social", "desen_social"},
        }
        namespaces_aceitos = aliases_namespace.get(namespace.lower(), {namespace.lower()})
        if placeholder_namespace in namespaces_aceitos:
            contexto_alvo = contexto
        else:
            contexto_alvo = alias_de_tabela.get(placeholder_namespace)

        if isinstance(contexto_alvo, dict):
            valor = _resolver_campo_com_alias(contexto_alvo, campo)
            if valor is not None:
                return _formatar_valor(valor)
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
    aliases = [namespace]
    if namespace.lower() == "demografia":
        aliases.append("demo")
    alternativas = "|".join(re.escape(alias) for alias in aliases)

    # Erro de digitação comum nos documentos: "namespace$.campo" em vez de
    # "namespace.$campo" (o "$" e o "." trocados de posição). Cobre também
    # o alias "demo" para o namespace "demografia".
    resultado = re.sub(
        rf"(?i)(?<![\w])({alternativas})\$\.",
        r"\1.$",
        resultado,
    )

    if namespace.lower() == "demografia":
        resultado = re.sub(r"(?i)(?<![\w])demo\.\$", "demografia.$", resultado)

    # Formato completo: macrotema.nome_do_csv.$campo.
    resultado = re.sub(
        rf"(?i)(?<![\w]){re.escape(namespace)}\."
        rf"{re.escape(namespace)}\.\$([A-Za-z_][\w]*)",
        _resolver_ou_manter,
        resultado,
    )

    # Formato usado em alguns documentos: namespace.$campo.
    resultado = re.sub(
        rf"(?i)(?<![\w]){re.escape(namespace)}\.\$([A-Za-z_][\w]*)",
        _resolver_ou_manter,
        resultado,
    )

    # Formato usado nos documentos: $Table.nome_da_tabela$campo.
    resultado = re.sub(
        r"\$(?:table|tabela|sheet|planilha)\.[A-Za-z_][\w]*\$([A-Za-z_][\w]*)",
        _resolver_ou_manter,
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
        _resolver_ou_manter,
        resultado,
    )

    for alias, valor in alias_map.items():
        resultado = re.sub(
            rf"\${re.escape(alias)}(?![\w])",
            str(valor),
            resultado,
        )

    resultado = re.sub(
        r'\{\{\s*(\w+)\s*\}\}',
        lambda m: str(contexto.get(m.group(1), m.group(0))),
        resultado,
    )

    return resultado
