import re
from decimal import Decimal

from utils.formatting import coerce_para_float, formatar_numero_ptbr

_MARCADOR_CAMPO_CONDICIONAL = re.compile(r"(?:[A-Za-z_][\w-]*\.)?\$([A-Za-z_][\w]*)")

_ALIASES_NAMESPACE = {
    "demografia": {"demografia", "demo"},
    "economia-renda": {"economia-renda", "economia"},
    "hidraulica": {"hidraulica", "seg_hidrica"},
    "saneamento": {"saneamento", "infraestrutura"},
    "meio-ambiente": {"meio-ambiente", "ambiente"},
    "desenvolvimento-social": {"desenvolvimento-social", "desen_social"},
}


# Cada operador é tentado nessa ordem contra o trecho de texto que segue um
# "$campo" na condição; a ordem importa porque frases mais específicas (ex.:
# "maior ou igual a") contêm substrings de frases mais genéricas (ex.: "igual
# a") e precisam ser checadas antes. Os grupos capturados (sempre inteiros no
# texto dos Docs) são os limites/limiares usados pela função de teste.
_OPERADORES_EDITORIAIS: list[tuple[re.Pattern, object]] = [
    (re.compile(r"de\s+(\d+)\s+a\s+(\d+)"), lambda v, a, b: a <= v <= b),
    (re.compile(r"entre\s+(\d+)\s+e\s+(\d+)"), lambda v, a, b: a <= v <= b),
    (re.compile(r"maior\s+ou\s+igual\s+a\s+(\d+)"), lambda v, n: v >= n),
    (re.compile(r"menor\s+ou\s+igual\s+a\s+(\d+)"), lambda v, n: v <= n),
    (re.compile(r"maior\s+que\s+(\d+)"), lambda v, n: v > n),
    (re.compile(r"menor\s+que\s+(\d+)"), lambda v, n: v < n),
    (re.compile(r"diferente\s+de\s+(\d+)"), lambda v, n: v != n),
    (re.compile(r"igual\s+a\s+(\d+)"), lambda v, n: v == n),
]

# Variante "campo A for <operador> campo B" (ex.: "educacao.$sem_instr_2000 for
# igual a educacao.$sem_instr_2022"): os operadores acima exigem um número
# literal (\d+) logo após a frase, então nunca casam quando o outro lado da
# comparação também é um "$campo". Só cobre os dois únicos casos usados hoje
# (igual/diferente); os operadores de faixa/ordem não têm uso campo-a-campo
# no momento.
_OPERADORES_CAMPO_A_CAMPO: list[tuple[re.Pattern, object]] = [
    (re.compile(r"diferente\s+de\s*$"), lambda a, b: a != b),
    (re.compile(r"igual\s+a\s*$"), lambda a, b: a == b),
]


def _parse_operador_campo_a_campo(trecho: str):
    for padrao, atende in _OPERADORES_CAMPO_A_CAMPO:
        if padrao.search(trecho):
            return atende
    return None

# Campos onde `None` (sem dado no banco) não pode ser tratado como zero: a
# ausência de dado é distinta de um valor zero de fato, e confundi-las
# afirmaria algo que a fonte de dados não garante (ver o caso histórico de
# `demografia.$centro_pop`). Lista explícita — e não automática pra qualquer
# campo único — porque em outros campos (ex.: contagens auxiliares que vêm
# NULL quando uma categoria simplesmente não se aplica) `None` equivaler a
# zero é o comportamento correto.
_CAMPOS_NULL_SENSIVEIS = {"centro_pop", "n_uc"}


def _parse_operador_editorial(trecho: str):
    for padrao, atende in _OPERADORES_EDITORIAIS:
        match = padrao.search(trecho)
        if match:
            return atende, tuple(float(grupo) for grupo in match.groups())
    return None


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

    # "campo A for igual a/diferente de campo B": dois marcadores e nada além
    # do operador entre eles — compara os dois valores resolvidos entre si,
    # em vez de cada campo contra um número literal.
    if len(matches) == 2:
        trecho_entre = expressao[matches[0].end():matches[1].start()].casefold()
        trecho_apos = expressao[matches[1].end():].casefold()
        atende_campo_a_campo = _parse_operador_campo_a_campo(trecho_entre)
        # Só assume campo-a-campo se não houver, depois do segundo campo, um
        # operador de número literal (que indicaria o formato "campo A for X
        # e campo B for Y" já suportado, não uma comparação entre os dois).
        if atende_campo_a_campo is not None and _parse_operador_editorial(trecho_apos) is None:
            return atende_campo_a_campo(valores[0], valores[1])

    operadores = []
    for indice, match in enumerate(matches):
        fim = matches[indice + 1].start() if indice + 1 < len(matches) else len(expressao)
        trecho = expressao[match.end():fim].casefold()
        operadores.append(_parse_operador_editorial(trecho))
    operador_compartilhado = next((op for op in reversed(operadores) if op), None)
    operadores = [op or operador_compartilhado for op in operadores]

    def atende(valor: float, operador) -> bool:
        if operador is None:
            return False
        funcao, argumentos = operador
        return funcao(valor, *argumentos)

    return all(atende(valor, operador) for valor, operador in zip(valores, operadores))


_CONDICAO_GINI = re.compile(
    r"(?i)^(?:para\s+)?quando\s+o\s+[íi]ndice\s+de\s+gini\s+for\s+"
    r"(maior\s+(?:e|ou)\s+igual\s+a|menor\s+que)\s+([\d]+(?:[.,]\d+)?)\s*:?\s*$"
)


def interpretar_blocos_condicionais(texto: str, contexto: dict) -> str:
    """Interpreta as instruções editoriais usadas nos documentos dos macrotemas.

    As linhas ``Para quando ...:`` controlam os parágrafos seguintes e não são
    exibidas. Condições de 2010 ficam subordinadas ao bloco indígena/quilombola
    imediatamente anterior. O documento de desenvolvimento social usa uma
    variante própria, sem "Para" e sem dois-pontos: ``Quando o índice de Gini
    for maior e igual a 0,5`` / ``... for menor que 0,5``.
    """
    resultado: list[str] = []
    bloco_ativo = True
    bloco_populacoes_ativo = True
    bloco_rua_ativo = True
    # "Para quando X:"/"Para quando NÃO-X:" simples (fora dos casos especiais
    # abaixo, que têm estado próprio e persistem de propósito) só devem gatear
    # o parágrafo seguinte; sem isso, o conteúdo incondicional que vem depois
    # herdaria o resultado da última condição avaliada e sumiria do relatório.
    aguardando_fim_de_bloco_simples = False
    # No Doc exportado, a regra "Para quando ...:" e o parágrafo que ela guarda
    # normalmente vêm em parágrafos separados (uma linha em branco entre os
    # dois, como em qualquer texto do Google Docs) — essa linha em branco não
    # pode ser tratada como "fim do bloco", senão o bloco reativa antes mesmo
    # do parágrafo guardado ser lido, e as duas versões (ex.: igual/diferente)
    # vazam juntas no relatório, não importa o dado. Só a primeira linha em
    # branco *depois* de já termos visto conteúdo do parágrafo guardado conta
    # como fim de bloco.
    bloco_simples_teve_conteudo = False

    for linha in texto.splitlines():
        limpa = linha.strip()

        if aguardando_fim_de_bloco_simples:
            if limpa:
                bloco_simples_teve_conteudo = True
            elif bloco_simples_teve_conteudo:
                bloco_ativo = True
                aguardando_fim_de_bloco_simples = False
                bloco_simples_teve_conteudo = False

        if re.match(r"(?i)^sequ[eê]ncia do texto,?\s*sem condi[cç][aã]o:?$", limpa):
            bloco_ativo = True
            bloco_populacoes_ativo = True
            aguardando_fim_de_bloco_simples = False
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
                elif len(campos) == 1 and campos <= _CAMPOS_NULL_SENSIVEIS:
                    (campo_unico,) = campos
                    bloco_ativo = (
                        _resolver_campo_com_alias(contexto, campo_unico) is not None
                        and atende
                    )
                else:
                    bloco_ativo = atende
                    aguardando_fim_de_bloco_simples = True
                    bloco_simples_teve_conteudo = False
                continue
            # Sem "$campo", não é uma instrução editorial de fato — é uma frase
            # comum do texto (ex.: "Para efeito de análise:") e deve ser mantida.

        condicao_gini = _CONDICAO_GINI.match(limpa)
        if condicao_gini:
            operador_texto, limite_texto = condicao_gini.groups()
            limite = float(limite_texto.replace(",", "."))
            gini = _resolver_campo_com_alias(contexto, "gini_2010")
            gini_numero = coerce_para_float(gini, default=None)
            if gini_numero is None:
                bloco_ativo = False
            elif "menor" in operador_texto.casefold():
                bloco_ativo = gini_numero < limite
            else:
                bloco_ativo = gini_numero >= limite
            aguardando_fim_de_bloco_simples = True
            continue

        if limpa.casefold() in {"síntese", "sintese"}:
            bloco_ativo = True
            bloco_populacoes_ativo = True
            bloco_rua_ativo = True
            aguardando_fim_de_bloco_simples = False

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

            # Município com levantamento de rua em 2022 mas ainda sem o de 2026:
            # o parágrafo padrão compara os dois anos e vazaria placeholders
            # crus (ex.: "$pop_rua_2026"). Texto provisório restrito a 2022,
            # sem a comparação — PENDENTE de validação com o time de
            # conteúdo/Doc antes de ir para produção.
            if bloco_ativo and bloco_rua_ativo and (
                _resolver_campo_com_alias(contexto, "pop_rua_2026") is None
            ):
                resultado.append(
                    "Outro grupo relevante para a caracterização da população "
                    "municipal é o de pessoas em situação de rua. Em 2022, "
                    "demografia.$nm_mun registrava demografia.$pop_rua_2022 "
                    "pessoas nessa condição. Entre as famílias em situação de "
                    "rua, demografia.$pop_rua_pobreza "
                    "(demografia.$pop_rua_pobreza_per)% estavam em situação de "
                    "pobreza, demografia.$pop_rua_br (demografia.$pop_rua_br_per)% "
                    "eram classificadas como de baixa renda e "
                    "demografia.$pop_rua_acima_br "
                    "(demografia.$pop_rua_acima_br_per)% possuíam renda acima de "
                    "meio salário mínimo. Além disso, "
                    "demografia.$pop_rua_bolsaf_2022 famílias em situação de rua "
                    "eram beneficiárias do Bolsa Família. Ainda não há "
                    "levantamento mais recente (2026) disponível na fonte "
                    "consultada para comparação."
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


def _formatar_valor(valor: object, decimais: int | None = None) -> str:
    if isinstance(valor, bool):
        return str(valor)
    if isinstance(valor, (int, float, Decimal)):
        numero = float(valor)
        if decimais is None:
            decimais = 0 if numero == int(numero) else 1
        return formatar_numero_ptbr(numero, decimais=decimais)
    return str(valor)


_SUFIXO_PRECISAO = re.compile(r"\$([A-Za-z_][\w]*):(\d+)\b")


def _extrair_precisoes(texto: str) -> tuple[str, dict[str, int]]:
    """Extrai sufixos de precisão dos placeholders (ex.: ``$idhm_2010:3``
    pede três casas decimais) e os remove do texto antes das demais
    substituições, mantendo o restante do placeholder intacto.

    O padrão global de ``_formatar_valor`` (uma casa para não-inteiros) não
    serve para todo o documento: o IDHM e o Gini usam três casas, e um corte
    de exibição em uma casa pode até mudar de faixa um valor perto de um
    limiar (ex.: Gini 0,542 exibido como "0,5"). Em vez de tornar o
    formatador ciente de cada campo, o próprio Doc pede a precisão que
    precisa.
    """
    precisoes: dict[str, int] = {}

    def _capturar(match: re.Match) -> str:
        precisoes[match.group(1)] = int(match.group(2))
        return f"${match.group(1)}"

    return _SUFIXO_PRECISAO.sub(_capturar, texto), precisoes


def _resolver_contexto_por_alias(contexto: dict, alias: str, namespace: str) -> dict:
    if alias == namespace.lower():
        return contexto

    valor_alias = contexto.get(alias)
    if isinstance(valor_alias, dict):
        return valor_alias

    return contexto


def substituir_placeholders(texto: str, contexto: dict, namespace: str = "demografia") -> str:
    texto, precisoes = _extrair_precisoes(texto)

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
        campo = match.group(1)
        valor = _resolver_campo_com_alias(contexto, campo)
        return (
            _formatar_valor(valor, precisoes.get(campo))
            if valor is not None
            else match.group(0)
        )

    def _substituir_dolar(match: re.Match) -> str:
        placeholder_namespace = match.group(1).lower()
        campo = match.group(2)

        namespaces_aceitos = _ALIASES_NAMESPACE.get(namespace.lower(), {namespace.lower()})
        if placeholder_namespace in namespaces_aceitos:
            contexto_alvo = contexto
        else:
            contexto_alvo = alias_de_tabela.get(placeholder_namespace)

        if isinstance(contexto_alvo, dict):
            valor = _resolver_campo_com_alias(contexto_alvo, campo)
            if valor is not None:
                return _formatar_valor(valor, precisoes.get(campo))
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

    # Normaliza os aliases de namespace usados nos documentos (ex.: "demo.$",
    # "desen_social.$", "economia.$") para o slug canônico do macrotema, para
    # que o formato "namespace.$campo" abaixo os reconheça.
    outros_aliases = _ALIASES_NAMESPACE.get(namespace.lower(), set()) - {namespace.lower()}
    if outros_aliases:
        alternativas_alias = "|".join(re.escape(alias) for alias in outros_aliases)
        resultado = re.sub(
            rf"(?i)(?<![\w-])(?:{alternativas_alias})\.\$",
            f"{namespace}.$",
            resultado,
        )

    # Erro de digitação comum nos documentos: "namespace$.campo" em vez de
    # "namespace.$campo" (o "$" e o "." trocados de posição). Cobre também
    # o alias "demo" para o namespace "demografia".
    alternativas = "|".join(
        re.escape(alias) for alias in outros_aliases | {namespace.lower()}
    )
    resultado = re.sub(
        rf"(?i)(?<![\w-])({alternativas})\$\.",
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

    # Namespace de outra view (ex.: "demografia.$nm_mun" num relatório de
    # saneamento): o prefixo indica a view de origem, mas os campos de
    # identidade e afins já vivem no contexto mesclado. Resolve o campo e
    # consome o prefixo inteiro — do contrário o passe de "$campo" simples
    # abaixo comeria só o "$campo" e deixaria o "demografia." órfão no texto.
    # Se o campo não existir, mantém o placeholder intacto (não meia-resolve).
    resultado = re.sub(
        r"(?i)(?<![\w])[A-Za-z_][\w-]*\.\$([A-Za-z_][\w]*)",
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
