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
# a") e precisam ser checadas antes. Os grupos capturados são os
# limites/limiares usados pela função de teste — aceitam decimal com vírgula
# (ex.: "maior ou igual a 0,5", usado no Gini) porque `\d+` sozinho truncava
# pro inteiro antes da vírgula (bug real: "menor que 0,5" virava "menor que
# 0", esvaziando a Síntese de desenvolvimento social pra qualquer Gini > 0).
_NUMERO_EDITORIAL = r"(\d+(?:[.,]\d+)?)"
_OPERADORES_EDITORIAIS: list[tuple[re.Pattern, object]] = [
    (re.compile(rf"de\s+{_NUMERO_EDITORIAL}\s+a\s+{_NUMERO_EDITORIAL}"), lambda v, a, b: a <= v <= b),
    (re.compile(rf"entre\s+{_NUMERO_EDITORIAL}\s+e\s+{_NUMERO_EDITORIAL}"), lambda v, a, b: a <= v <= b),
    # "maior E igual a" também aparece no Doc (não só "maior OU igual a") —
    # mesma variante que _CONDICAO_GINI já aceitava, mas esta condição cai no
    # caminho genérico (tem "$campo" na expressão) e nunca chegava lá.
    (re.compile(rf"maior\s+(?:e|ou)\s+igual\s+a\s+{_NUMERO_EDITORIAL}"), lambda v, n: v >= n),
    (re.compile(rf"menor\s+(?:e|ou)\s+igual\s+a\s+{_NUMERO_EDITORIAL}"), lambda v, n: v <= n),
    (re.compile(rf"maior\s+que\s+{_NUMERO_EDITORIAL}"), lambda v, n: v > n),
    (re.compile(rf"menor\s+que\s+{_NUMERO_EDITORIAL}"), lambda v, n: v < n),
    (re.compile(rf"diferente\s+de\s+{_NUMERO_EDITORIAL}"), lambda v, n: v != n),
    (re.compile(rf"igual\s+a\s+{_NUMERO_EDITORIAL}"), lambda v, n: v == n),
    # Variante simbólica de "igual a N" (ex.: "for = 0"); não conflita com
    # ">="/">" porque essas formas só aparecem nas condições de rua, tratadas
    # à parte por _avaliar_condicao_demografia antes de chegar aqui.
    (re.compile(rf"(?<![<>!])=\s*{_NUMERO_EDITORIAL}"), lambda v, n: v == n),
]

# Variante "campo A for <operador> campo B": os operadores acima exigem um
# número literal, então não casam quando o outro lado também é "$campo". Só
# cobre igual/diferente, os únicos casos usados hoje.
_OPERADORES_CAMPO_A_CAMPO: list[tuple[re.Pattern, object]] = [
    (re.compile(r"diferente\s+de\s*$"), lambda a, b: a != b),
    (re.compile(r"igual\s+a\s*$"), lambda a, b: a == b),
]


# Campos de texto da view que carregam número + unidade por extenso, como
# "12,2 pontos percentuais" ou "0 ponto percentual" (var_coleta_pp,
# var_esgoto_pp). `coerce_para_float` só entende "12,2", então o sufixo
# derrubava o valor para 0 e invertia condições do tipo "diferente de 0": o
# relatório afirmava "valor igual ao registrado em 2010" num município que
# variou 12,2 p.p. Extrai o número que abre a string; texto sem número algum
# (ex.: "crescimento") continua caindo no default de quem chama.
_NUMERO_NO_INICIO = re.compile(r"^\s*(-?\d+(?:[.,]\d+)?)")


def _numero_do_campo(valor: object) -> float | None:
    """Valor do campo como número, aceitando texto com unidade por extenso.
    Devolve None quando não há número nenhum na string."""
    if isinstance(valor, str):
        match = _NUMERO_NO_INICIO.match(valor)
        if not match:
            return None
        valor = match.group(1)
    return coerce_para_float(valor, default=None)


def _parse_operador_campo_a_campo(trecho: str):
    for padrao, atende in _OPERADORES_CAMPO_A_CAMPO:
        if padrao.search(trecho):
            return atende
    return None

# Campos onde `None` (sem dado) não pode virar zero — confundir os dois
# afirmaria algo que a fonte não garante (caso histórico de
# `demografia.$centro_pop`). Lista explícita: em outros campos, None==zero
# é o comportamento correto.
# `tend_sem_instr_per_dado` vem "sem dados" nos municípios sem Censo 2000
# (fundados depois de 2000); sem essa entrada, a condição de educação
# ("igual a 0") tratava a ausência de série histórica como "não houve
# mudança" (revisão editorial de Educação, 25/09/2026).
# `asd_per_2021` é NULL em Fernando de Noronha (sem classificação de aridez);
# como 0, o município recebia "nenhuma parte do território em área suscetível à
# desertificação" (revisão editorial de Meio Ambiente, 25/09/2026).
# A regra vale também em condição composta: a Síntese de meio ambiente cruza
# n_uc com asd_per_2021 numa condição só.
_CAMPOS_NULL_SENSIVEIS = {"centro_pop", "n_uc", "tend_sem_instr_per_dado", "asd_per_2021"}


def _normalizar_condicao_editorial(linha: str) -> str:
    # A exportação Markdown do Docs intercala negrito e escapa operadores e
    # underscores; o texto obtido diretamente da API já vem sem essas marcas.
    linha = re.sub(r"\\([_=>])", r"\1", linha.strip())
    return linha.replace("**", "").replace("\u00a0", " ").strip()


def _avaliar_condicao_demografia(expressao: str, contexto: dict) -> bool | None:
    """Condições novas do documento de demografia, inclusive comparações de campos."""
    campos = _MARCADOR_CAMPO_CONDICIONAL.findall(expressao)
    if not campos:
        return None

    def valor(campo: str) -> float | None:
        if campo == "pop_rua_2022" and "pop_rua_2026" in contexto:
            return coerce_para_float(contexto.get(campo), default=None)
        bruto = _resolver_campo_com_alias(contexto, campo)
        return coerce_para_float(bruto, default=None)

    if "dif_etaria_09_60" in campos:
        # dif_etaria_09_60 é a magnitude (view e cálculo local); o sinal vem de
        # dif_etaria_09_60_dado = idosos - crianças. O Doc chama de "positivo" o
        # cenário com mais crianças, ou seja, _dado < 0.
        diferenca = valor("dif_etaria_09_60_dado")
        if diferenca is None:
            return False
        return diferenca < 0 if "positivo" in expressao else diferenca > 0

    # O Doc condiciona por $cres_pop ("for 0" / "for maior ou menor que 0"), não
    # só por $cres_pop_analise. Sem isso a condição caía no avaliador genérico,
    # que só entende "menor que 0": com a view mandando cres_pop em módulo
    # (#159), o parágrafo de dinâmica populacional sumia pra toda cidade.
    if "cres_pop_analise" in campos or "cres_pop" in campos:
        crescimento = valor("cres_pop")
        if crescimento is None:
            return False
        return crescimento != 0 if "maior ou menor" in expressao else crescimento == 0

    if not any(campo.startswith("pop_rua_") or campo == "pop_familias_rua_2026" for campo in campos):
        return None

    # Ausência de levantamento não significa zero pessoas.
    if any(valor(campo) is None for campo in campos):
        return False

    partes = list(_MARCADOR_CAMPO_CONDICIONAL.finditer(expressao))
    for indice, match in enumerate(partes):
        campo = match.group(1)
        fim = partes[indice + 1].start() if indice + 1 < len(partes) else len(expressao)
        trecho = expressao[match.end():fim].casefold()
        atual = valor(campo)
        # O Doc escreve tanto "= $campo" quanto "for igual a $campo"; sem a
        # forma por extenso, a comparação caía no `continue` abaixo (não há
        # dígito no trecho) e era ignorada — "todas beneficiárias" batia pra
        # qualquer total de famílias.
        if indice + 1 < len(partes) and re.search(r"(?:for\s*)?(?:=|igual\s+a)\s*$", trecho):
            if campo == "pop_familias_rua_2026" and atual == 0:
                return False
            if atual != valor(partes[indice + 1].group(1)):
                return False
            continue
        operador = re.search(r"(?:for\s*)?(>=|>|=|maior\s+que|igual\s+a)?\s*(\d+)", trecho)
        if operador is None:
            # "X e Y for 0" aplica o mesmo limiar aos dois campos.
            trecho_final = expressao[partes[-1].end():].casefold()
            operador = re.search(r"(?:for\s*)?(>=|>|=|maior\s+que|igual\s+a)?\s*(\d+)", trecho_final)
        if operador is None:
            continue
        sinal, limite_texto = operador.groups()
        limite = float(limite_texto)
        if sinal in {">", "maior que"} and not atual > limite:
            return False
        if sinal == ">=" and not atual >= limite:
            return False
        if sinal not in {">", ">=", "maior que"} and atual != limite:
            return False
    # Uma condição diz "família recebe Bolsa Família = 0" sem marcador.
    return not (
        "família recebe bolsa família = 0" in expressao
        and valor("pop_rua_bolsaf_2026") != 0
    )


def _parse_operador_editorial(trecho: str):
    for padrao, atende in _OPERADORES_EDITORIAIS:
        match = padrao.search(trecho)
        if match:
            return atende, tuple(
                float(grupo.replace(",", ".")) for grupo in match.groups()
            )
    return None


# Separador das condições compostas do Doc: "<comparação> e <comparação>".
# Os textos das condicionais são curtos e não têm "e" em outro papel.
_CONJUNCAO = re.compile(r"(?i)\s+e\s+")

# vacina_meta/vacina_nao_meta trazem uma lista de nomes de vacina (ou o
# literal "todas"/"nenhuma" quando a lista é total/vazia) — texto, não
# número. O caminho numérico de _avaliar_condicao_editorial forçaria esses
# valores para 0.0 e "for todas"/"for nenhuma" nunca bateriam.
_LITERAL_VAZIO_VACINA = {"vacina_meta": "todas", "vacina_nao_meta": "nenhuma"}


def _avaliar_condicao_vacina(expressao: str, contexto: dict) -> bool | None:
    """Condições do Doc de saúde: "vacina_meta for todas" / "vacina_nao_meta
    for nenhuma", isoladas, combinadas entre si ou com outro campo via "e".
    Devolve None quando a expressão não menciona nenhum dos dois campos, para
    cair no caminho numérico. Uma parte sobre outro campo (não vacina_*) é
    delegada a esse mesmo caminho numérico, avaliada só para aquela parte —
    sem isso, a mistura caía inteira no numérico e forçava vacina_meta/
    vacina_nao_meta (texto) para 0.0, sempre reprovando em silêncio."""
    campos = set(_MARCADOR_CAMPO_CONDICIONAL.findall(expressao))
    if not campos & set(_LITERAL_VAZIO_VACINA):
        return None

    for parte in _CONJUNCAO.split(expressao):
        matches = list(_MARCADOR_CAMPO_CONDICIONAL.finditer(parte))
        if len(matches) != 1:
            return None
        campo = matches[0].group(1)
        literal = _LITERAL_VAZIO_VACINA.get(campo)
        if literal is None:
            if not _avaliar_condicao_editorial(matches, parte, contexto):
                return False
            continue
        trecho = parte[matches[0].end():].casefold()
        if literal not in trecho:
            return None
        valor = _resolver_campo_com_alias(contexto, campo)
        # Sem levantamento, o campo não é "igual" nem "diferente" do literal —
        # tratar None como "" faria "diferente de todas/nenhuma" bater sem
        # dado nenhum (relatório afirmaria situação mista sem evidência).
        if valor is None:
            return False
        valor_texto = str(valor).strip().casefold()
        igual = valor_texto == literal
        if "diferente" in trecho:
            if igual:
                return False
        elif not igual:
            return False
    return True


def _avaliar_comparacao_campo_a_campo(expressao: str, contexto: dict) -> bool | None:
    """Avalia UMA comparação "campo A for igual a/diferente de campo B".
    Devolve None quando o trecho não tem essa forma (dois campos e nada além
    do operador entre eles), para quem chama cair no caminho numérico."""
    matches = list(_MARCADOR_CAMPO_CONDICIONAL.finditer(expressao))
    if len(matches) != 2:
        return None

    trecho_entre = expressao[matches[0].end():matches[1].start()].casefold()
    atende = _parse_operador_campo_a_campo(trecho_entre)
    if atende is None:
        return None
    # Um operador com número literal depois do segundo campo indica o formato
    # "campo A for X e campo B for Y", que é numérico, não campo-a-campo.
    if _parse_operador_editorial(expressao[matches[1].end():].casefold()) is not None:
        return None

    def numero(match: re.Match) -> float | None:
        return _numero_do_campo(_resolver_campo_com_alias(contexto, match.group(1)))

    valor_a, valor_b = numero(matches[0]), numero(matches[1])
    # Ausência de levantamento de um lado (ex.: sem_instr_2000 = "sem dados"
    # num município sem censo 2000) não pode virar 0 — o município passaria
    # a bater "diferente de" contra o valor real de 2022 só por falta de
    # dado, afirmando uma variação que a fonte não confirma.
    if valor_a is None or valor_b is None:
        return False

    return atende(valor_a, valor_b)


def _avaliar_condicao_editorial(
    matches: list[re.Match], expressao: str, contexto: dict
) -> bool:
    campos = [match.group(1) for match in matches]

    def numero_bruto(campo: str) -> float | None:
        return _numero_do_campo(_resolver_campo_com_alias(contexto, campo))

    def numero(campo: str) -> float:
        numero_do_campo = numero_bruto(campo)
        return 0.0 if numero_do_campo is None else numero_do_campo

    valores = [numero(campo) for campo in campos]

    # Condição composta: "campo A ... campo B e campo C ... campo D" (as
    # quatro versões do parágrafo de síntese do Doc de saneamento). Cada
    # comparação é avaliada por si e todas precisam passar. Só entra aqui se
    # TODAS as partes forem campo-a-campo; do contrário segue o caminho
    # numérico, que já cobre "campo A for X e campo B for Y".
    if len(matches) > 2:
        partes = _CONJUNCAO.split(expressao)
        if len(partes) > 1:
            avaliadas = [
                _avaliar_comparacao_campo_a_campo(parte, contexto) for parte in partes
            ]
            if all(resultado is not None for resultado in avaliadas):
                return all(avaliadas)

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
            # Ausência de levantamento num dos campos (ex.: sem_instr_2000 =
            # "sem dados" num município sem censo 2000) não pode virar 0 —
            # bateria "diferente de" contra o valor real do outro campo só
            # por falta de dado, afirmando uma variação que a fonte não
            # confirma.
            if numero_bruto(campos[0]) is None or numero_bruto(campos[1]) is None:
                return False
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


def _avaliar_condicoes_de_rua(texto: str, contexto: dict) -> tuple[bool, bool]:
    """Pré-varre o Doc por condicionais "Para quando ...pop_rua...:" sem
    alterar o parse principal. Devolve (o Doc tem condicionais próprias pra
    isso, alguma bate pra este contexto) — decide se o fallback genérico
    ainda deve rodar (PR #112: antes, só ver a condicional já desligava o
    fallback, batendo ou não).
    """
    # Guarda barata: evita varrer linha a linha o Doc inteiro de todo
    # macrotema (só demografia usa isso) quando não há nem menção a rua.
    if "pop_rua" not in texto and "pop_familias_rua" not in texto:
        return False, False

    tem_condicoes = False
    alguma_bateu = False
    for linha in texto.splitlines():
        limpa = _normalizar_condicao_editorial(linha)
        condicao = re.match(r"(?i)^para(?:\s+quando)?\s+(.+?):\s*(.*)$", limpa)
        if not condicao:
            continue
        expressao = condicao.group(1).casefold()
        matches = list(_MARCADOR_CAMPO_CONDICIONAL.finditer(expressao))
        campos = {match.group(1) for match in matches}
        if not any(
            campo.startswith("pop_rua_") or campo == "pop_familias_rua_2026"
            for campo in campos
        ):
            continue
        tem_condicoes = True
        especial = _avaliar_condicao_demografia(expressao, contexto)
        atende = (
            especial
            if especial is not None
            else _avaliar_condicao_editorial(matches, expressao, contexto)
        )
        if atende:
            alguma_bateu = True
    return tem_condicoes, alguma_bateu


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
    # Não mutado durante o parse (ver _avaliar_condicoes_de_rua).
    bloco_rua_tem_condicoes, bloco_rua_condicional = _avaliar_condicoes_de_rua(
        texto, contexto
    )
    bloco_rua_fallback_emitido = False
    # "Para quando X:" simples só gateia o parágrafo seguinte; sem isso, o
    # conteúdo incondicional depois herdaria a última condição e sumiria.
    aguardando_fim_de_bloco_simples = False
    # A linha em branco entre "Para quando ...:" e seu parágrafo não conta
    # como "fim do bloco" — senão ele reativa antes do parágrafo ser lido e
    # as duas versões (igual/diferente) vazam juntas. Só a primeira linha em
    # branco *depois* de já termos visto conteúdo do parágrafo conta.
    bloco_simples_teve_conteudo = False

    for linha in texto.splitlines():
        limpa = _normalizar_condicao_editorial(linha)

        # Os marcadores de gráfico ficam depois das alternativas condicionais
        # no Google Docs e pertencem à seção inteira, não à última alternativa.
        # Sem uma linha vazia antes do marcador, a condição anterior ainda
        # estaria ativa e poderia apagar o gráfico mesmo com o PNG gerado.
        if re.fullmatch(r"(?:%%|\*)\w+(?:\+\w+)*", limpa):
            bloco_ativo = True
            aguardando_fim_de_bloco_simples = False
            bloco_simples_teve_conteudo = False
            resultado.append(linha)
            continue

        # "#!Fontes"/"#!Conteúdos relacionados" pertencem ao documento
        # inteiro, não à última condicional avaliada; sem este reset, uma
        # condicional órfã e falsa logo acima engoliria o marcador (PR #116).
        if re.match(r"(?i)^#!", limpa):
            bloco_ativo = True
            aguardando_fim_de_bloco_simples = False
            bloco_simples_teve_conteudo = False
            resultado.append(linha)
            continue

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

        condicao = re.match(r"(?i)^para(?:\s+quando)?\s+(.+?):\s*(.*)$", limpa)
        if condicao:
            expressao = condicao.group(1).casefold()
            matches = list(_MARCADOR_CAMPO_CONDICIONAL.finditer(expressao))
            if matches:
                campos = {match.group(1) for match in matches}
                especial = _avaliar_condicao_demografia(expressao, contexto)
                if especial is None:
                    especial = _avaliar_condicao_vacina(expressao, contexto)
                atende = especial if especial is not None else _avaliar_condicao_editorial(matches, expressao, contexto)
                # Sem dado num campo null-sensível, nenhuma condição sobre ele
                # vale, simples ou composta. Antes era um ramo à parte, só para
                # condição de um campo e sem o fim de bloco do ramo comum
                # (5742bdb): o texto depois do parágrafo herdava a condição.
                # "Sem dado" é não ter número: None da view, NaN do fallback de
                # CSV (pandas) ou texto como "sem dados".
                if any(
                    campo in _CAMPOS_NULL_SENSIVEIS
                    and _numero_do_campo(_resolver_campo_com_alias(contexto, campo)) is None
                    for campo in campos
                ):
                    atende = False
                # Blocos persistentes (indígena/quilombola) guardam vários
                # parágrafos além do primeiro; conteúdo inline nessa mesma
                # linha não pode reativar bloco_ativo cedo demais e vazar os
                # parágrafos seguintes de um bloco que deveria ficar False.
                if campos & {"pop_ind_2022", "pop_qui"}:
                    bloco_populacoes_ativo = atende
                    bloco_ativo = atende
                    bloco_e_persistente = True
                elif "pop_ind_2010" in campos:
                    bloco_ativo = bloco_populacoes_ativo and atende
                    bloco_e_persistente = True
                else:
                    bloco_ativo = atende
                    aguardando_fim_de_bloco_simples = True
                    bloco_simples_teve_conteudo = False
                    bloco_e_persistente = False
                if condicao.group(2) and not bloco_e_persistente:
                    if bloco_ativo:
                        resultado.append(condicao.group(2))
                    bloco_ativo = True
                    aguardando_fim_de_bloco_simples = False
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

        # Fallback pro parágrafo de situação de rua quando os dados faltam.
        # Com condicionais próprias no Doc, bloco_ativo aqui só reflete a
        # última condição (já False) — por isso bloco_ativo_fallback abaixo
        # não depende só dele.
        if (
            not bloco_rua_condicional
            and not bloco_rua_fallback_emitido
            and re.match(
                r"(?i)^outro grupo relevante para a caracteriza[cç][aã]o da "
                r"popula[cç][aã]o municipal",
                limpa,
            )
        ):
            bloco_ativo_fallback = bloco_ativo or bloco_rua_tem_condicoes
            bloco_rua_ativo = _resolver_campo_com_alias(contexto, "pop_rua_2022") is not None
            if bloco_ativo_fallback and not bloco_rua_ativo:
                nome_mun = _resolver_campo_com_alias(contexto, "nm_mun") or "o município"
                resultado.append(
                    f"Não foram encontrados registros de pessoas em situação de rua "
                    f"para {nome_mun} na fonte de dados consultada. Contudo, esse "
                    "resultado deve ser interpretado considerando os limites da base "
                    "de dados utilizada, não sendo suficiente, por si só, para "
                    "afastar a presença dessa população no município."
                )
                bloco_rua_fallback_emitido = True
                continue

            # Só 2022, sem 2026 ainda: texto provisório restrito a 2022 —
            # PENDENTE de validação com o time de conteúdo/Doc.
            if bloco_ativo_fallback and bloco_rua_ativo and (
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
                bloco_rua_fallback_emitido = True
                continue

            # Dados completos, mas nenhuma condição do Doc cobre a
            # combinação (lacuna editorial) — descarta em vez de vazar
            # placeholder sem valor.
            if bloco_rua_tem_condicoes:
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
        return round(float(valor_base) / float(total) * 100, 2)
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
        "pop_familias_rua_2026": "familias_rua_total",
        "pop_rua_bolsaf_2026": "familias_rua_bf",
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
                crescimento_numero = float(crescimento)
            except (TypeError, ValueError):
                crescimento_numero = None
            if crescimento_numero is not None:
                if crescimento_numero == 0:
                    return "estabilidade"
                return "crescimento" if crescimento_numero > 0 else "redução"

    valor = _resolver_percentual_derivado(contexto, campo)
    if valor is not None:
        return valor

    return None


# Decimal com ponto guardado em coluna de texto (ex.: esgoto_rede_2000 =
# "4.4"). Sem isso o valor escapa da formatação pt-BR e o relatório mistura
# "4.4%" com "7,3%" na mesma frase. Só casa o que é número decimal puro:
# string inteira ("2801108", código de município) fica intacta, para não
# ganhar separador de milhar, e texto com unidade ("12,2 pontos percentuais")
# também não casa.
_TEXTO_DECIMAL_COM_PONTO = re.compile(r"^-?\d+\.\d+$")


# Rede de segurança pra campos que têm uma precisão editorial fixa por
# convenção (IDHM/Gini/subíndices sempre 3 casas, renda per capita sempre 2):
# o Doc de desenvolvimento social já perdeu os sufixos ``:3``/``:2`` sem
# querer numa edição (achado em revisão, antes de ir pro main), o que caía no
# padrão global de 1 casa (abaixo) e cortava a precisão. Escopado por
# namespace pra não valer, sem querer, pra um campo de outro macrotema que só
# por acaso comece com o mesmo prefixo. O sufixo no Doc ainda tem prioridade
# — isto só cobre a falta dele.
_PRECISAO_PADRAO_POR_NAMESPACE: dict[str, tuple[tuple[re.Pattern, int], ...]] = {
    "desenvolvimento-social": (
        (re.compile(r"(?i)^(?:idhm|gini|subindice\d*)(?:_|$)"), 3),
        (re.compile(r"(?i)^renda_\d{4}$"), 2),
    ),
}


def _precisao_padrao_editorial(namespace: str, campo: str) -> int | None:
    for padrao, decimais in _PRECISAO_PADRAO_POR_NAMESPACE.get(namespace.lower(), ()):
        if padrao.match(campo):
            return decimais
    return None


# Campos de ano não devem levar separador de milhar ("2.023"): são rótulo de
# período, não quantidade. Lista explícita porque nenhum padrão de nome serve:
# `ultimo_junho` é ano e não tem "ano" no nome, e `dose_etario_1_ano` termina
# em "_ano" mas é contagem de doses (32.211).
_CAMPOS_ANO = {
    "ano",
    "year",
    "ano_menor_mortalidade",
    "ano_criacao_uc1",
    "ultimo_junho",
    "ultimo_jun",
    "ano_referencia_finalidade",
}


def _formatar_valor(valor: object, decimais: int | None = None, campo: str = "") -> str:
    if isinstance(valor, bool):
        return str(valor)
    if isinstance(valor, str) and _TEXTO_DECIMAL_COM_PONTO.match(valor.strip()):
        valor = float(valor)
    if isinstance(valor, (int, float, Decimal)):
        numero = float(valor)
        if decimais is None:
            decimais = 0 if numero == int(numero) else 2
        if campo.lower() in _CAMPOS_ANO and decimais == 0:
            return str(int(numero))
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


# Marca de campo que resolveu para vazio: "US$ $valor $unid)" com unidade vazia
# deixava "US$ 617 )". Só esse espaço some; o espaçamento do Doc fica.
_CAMPO_VAZIO = "\x00"


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

    def _precisao(campo: str) -> int | None:
        explicita = precisoes.get(campo)
        if explicita is not None:
            return explicita
        return _precisao_padrao_editorial(namespace, campo)

    def _resolver_ou_manter(match: re.Match) -> str:
        campo = match.group(1)
        valor = _resolver_campo_com_alias(contexto, campo)
        if valor is None:
            return match.group(0)
        return _formatar_valor(valor, _precisao(campo), campo) or _CAMPO_VAZIO

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
                return _formatar_valor(valor, _precisao(campo), campo) or _CAMPO_VAZIO
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
    # saneamento): resolve contra o contexto mesclado e consome o prefixo
    # inteiro — senão o passe de "$campo" simples abaixo deixaria o
    # "demografia." órfão no texto.
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

    resultado = re.sub(rf"[ \t]*{_CAMPO_VAZIO}(?=[),.;])", "", resultado)
    return resultado.replace(_CAMPO_VAZIO, "")
