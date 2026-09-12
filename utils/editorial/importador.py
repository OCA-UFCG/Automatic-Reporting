"""Converte o texto exportado de um Google Doc no contrato do painel.

É a ferramenta da Fase 0: roda uma vez por macrotema, produz o contrato inicial
e um **relatório de divergências** dizendo, item a item, onde o contrato passa
a se comportar de forma diferente do Doc.

A divergência não é efeito colateral — é o ponto. O parser atual tem operadores
que falham fechado (``for negativo``, ``for positivo``, ``for 0%``) e um que
casa errado (``for maior ou menor que 0%`` vira ``< 0``). O importador emite a
regra que o editor quis escrever e registra a diferença, para que a comparação
de paridade da Fase 1 saiba de antemão o que esperar.

Cada divergência é **provada**, não afirmada: a frase do Doc é interpretada
pelos dois parsers e os dois resultados são comparados sobre uma bateria de
valores de prova.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from utils.editorial.contrato import SLOT_FONTES
from utils.editorial.regras import avaliar_regra
from utils.render.placeholders import (
    _CAMPOS_NULL_SENSIVEIS,
    _MARCADOR_CAMPO_CONDICIONAL,
    _parse_operador_editorial,
)

# Valores usados para provar que a regra nova e a antiga divergem. Cobrem
# negativo, zero, fracionário e os limiares inteiros que aparecem nos Docs.
VALORES_DE_PROVA = (-10, -1, -0.5, 0, 0.5, 1, 2, 5, 10, 100)

_NUMERO = r"(\d+(?:[.,]\d+)?)"

# Ordem importa, como na tabela original: frases específicas contêm substrings
# das genéricas. "maior ou menor que" vem antes de "menor que" — é exatamente
# a inversão que faz o parser atual ler "≠ 0" como "< 0".
_FRASES_OPERADOR: list[tuple[re.Pattern, str]] = [
    (re.compile(rf"de\s+{_NUMERO}\s+a\s+{_NUMERO}"), "entre"),
    (re.compile(rf"entre\s+{_NUMERO}\s+e\s+{_NUMERO}"), "entre"),
    (re.compile(rf"maior\s+ou\s+menor\s+que\s+{_NUMERO}"), "diferente"),
    (re.compile(rf"maior\s+(?:ou|e)\s+igual\s+a\s+{_NUMERO}"), "maior_igual"),
    (re.compile(rf"menor\s+(?:ou|e)\s+igual\s+a\s+{_NUMERO}"), "menor_igual"),
    (re.compile(rf"maior\s+(?:que|do\s+que)\s+{_NUMERO}"), "maior"),
    (re.compile(rf"menor\s+(?:que|do\s+que)\s+{_NUMERO}"), "menor"),
    (re.compile(rf"diferente\s+de\s+{_NUMERO}"), "diferente"),
    (re.compile(rf"igual\s+a\s+{_NUMERO}"), "igual"),
    (re.compile(r"\bnegativ[oa]\b"), "negativo"),
    (re.compile(r"\bpositiv[oa]\b"), "positivo"),
    # Último recurso: "for 0%, então" — número solto logo após o "for".
    (re.compile(rf"^\s*(?:for|é|e)\s+{_NUMERO}\s*%?"), "igual"),
]

# Mesmas frases, mas terminando sem número: o alvo da comparação é o `$campo`
# que vem logo depois. O parser dos Docs não tem essa forma — a condição falha
# e o parágrafo some do relatório em qualquer município.
_FRASES_OPERADOR_ENTRE_CAMPOS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"maior\s+(?:ou|e)\s+igual\s+a\s*$"), "maior_igual"),
    (re.compile(r"menor\s+(?:ou|e)\s+igual\s+a\s*$"), "menor_igual"),
    (re.compile(r"maior\s+(?:que|do\s+que)\s*$"), "maior"),
    (re.compile(r"menor\s+(?:que|do\s+que)\s*$"), "menor"),
    (re.compile(r"diferente\s+(?:de|que)\s*$"), "diferente"),
    (re.compile(r"igual\s+a\s*$"), "igual"),
]

_INSTRUCAO_CONDICIONAL = re.compile(r"(?i)^para(?:\s+quando)?\s+(.+?):\s*$")
_SEM_CONDICAO = re.compile(r"(?i)^sequ[eê]ncia do texto,?\s*sem condi[cç][aã]o:?$")
_CONDICAO_GINI = re.compile(
    r"(?i)^(?:para\s+)?quando\s+o\s+[íi]ndice\s+de\s+gini\s+for\s+"
    r"(maior\s+(?:e|ou)\s+igual\s+a|menor\s+que)\s+([\d]+(?:[.,]\d+)?)\s*:?\s*$"
)
_LEGENDA_FIGURA = re.compile(r"(?i)^figura\s+[a-z0-9&]+\s*[-–—]")
_MARCADOR_GRAFICO = re.compile(r"^\s*(?:\*|%%)([a-z_][a-z0-9_]*)\s*$", re.IGNORECASE)
_ITEM_DE_LISTA = re.compile(r"^\s*(?:[-•]|\*)\s+(.*)$")
_CABECALHO_CAIXA = re.compile(r"^#!\s*(.*)$")
# "Síntese" e afins: linha curta, sem placeholder e sem pontuação final.
_TITULO_DE_SECAO = re.compile(r"^[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9 ,'\-]{0,58}$")

# Campos que abrem o grupo indígena/quilombola. No parser atual isso é a
# variável de estado `bloco_populacoes_ativo`; no contrato vira uma seção que
# contém os blocos subordinados, e o aninhamento explícito substitui o estado.
_CAMPOS_GRUPO_POPULACOES = {"pop_ind_2022", "pop_qui"}
_CAMPOS_SUBORDINADOS = {"pop_ind_2010"}


@dataclass
class Divergencia:
    """Um ponto onde o contrato não reproduz o comportamento atual do Doc."""

    tipo: str
    linha: int
    trecho: str
    legado: str
    contrato: str
    prova: str = ""

    def como_markdown(self) -> str:
        corpo = (
            f"- **linha {self.linha} — {self.tipo}**\n"
            f"  - Doc: `{self.trecho}`\n"
            f"  - Hoje: {self.legado}\n"
            f"  - Contrato: {self.contrato}\n"
        )
        if self.prova:
            corpo += f"  - Prova: {self.prova}\n"
        return corpo


@dataclass
class ResultadoImportacao:
    contrato: dict[str, Any]
    divergencias: list[Divergencia] = field(default_factory=list)


def _numero(texto: str) -> float:
    valor = float(texto.replace(".", "").replace(",", ".")) if "," in texto else float(texto)
    return valor


def parsear_frase_operador(trecho: str) -> tuple[str, Any] | None:
    """Frase em português depois do ``$campo`` -> (operador nomeado, valor).

    Devolve ``None`` quando nenhuma frase conhecida aparece — aí o importador
    registra a condição como não interpretada em vez de inventar uma regra.
    """
    minusculo = trecho.casefold()
    for padrao, op in _FRASES_OPERADOR:
        match = padrao.search(minusculo)
        if not match:
            continue
        if op == "entre":
            return "entre", [_numero(match.group(1)), _numero(match.group(2))]
        if op == "negativo":
            return "menor", 0
        if op == "positivo":
            return "maior", 0
        return op, _numero(match.group(1))
    return None


def parsear_frase_entre_campos(trecho: str) -> str | None:
    """Operador cujo alvo é o campo seguinte, e não um número literal."""
    minusculo = trecho.casefold().rstrip()
    for padrao, op in _FRASES_OPERADOR_ENTRE_CAMPOS:
        if padrao.search(minusculo):
            return op
    return None


def _avaliar_legado(trecho: str, valor: float) -> bool:
    operador = _parse_operador_editorial(trecho.casefold())
    if operador is None:
        # Sem operador reconhecido, _avaliar_condicao_editorial devolve False:
        # o bloco nunca aparece.
        return False
    funcao, argumentos = operador
    return bool(funcao(valor, *argumentos))


def _provar_divergencia(trecho: str, op: str, valor: Any) -> str:
    """Lista os valores em que a regra nova e a antiga discordam. Vazio se batem."""
    condicao = {"campo": "x", "op": op, "valor": valor}
    discordancias = []
    for prova in VALORES_DE_PROVA:
        novo = avaliar_regra({"condicoes": [condicao]}, {"x": prova}).inclui
        legado = _avaliar_legado(trecho, prova)
        if novo != legado:
            discordancias.append(
                f"{prova:g} → hoje {'mostra' if legado else 'esconde'}, "
                f"contrato {'mostra' if novo else 'esconde'}"
            )
    return "; ".join(discordancias)


def parsear_condicao(
    expressao: str, linha: int
) -> tuple[list[dict], list[Divergencia]]:
    """``demografia.$pop_ind_2022 e demografia.$pop_qui for diferente de 0``
    -> duas condições nomeadas, mais as divergências encontradas."""
    matches = list(_MARCADOR_CAMPO_CONDICIONAL.finditer(expressao))
    if not matches:
        return [], []

    trechos: list[str] = []
    for i, match in enumerate(matches):
        fim = matches[i + 1].start() if i + 1 < len(matches) else len(expressao)
        trechos.append(expressao[match.end() : fim])

    # Comparação entre dois campos: "$a for igual a $b". Consome os dois campos
    # de uma vez, porque o segundo é o alvo e não uma condição própria.
    condicoes_entre_campos: list[dict] = []
    consumidos: set[int] = set()
    for i, trecho in enumerate(trechos[:-1]):
        if i in consumidos:
            continue
        op = parsear_frase_entre_campos(trecho)
        if op is None:
            continue
        condicoes_entre_campos.append(
            {
                "campo": matches[i].group(1),
                "op": op,
                "valor": {"campo": matches[i + 1].group(1)},
            }
        )
        consumidos.update({i, i + 1})

    if condicoes_entre_campos:
        return condicoes_entre_campos, [
            Divergencia(
                tipo="comparação entre campos",
                linha=linha,
                trecho=expressao.strip(),
                legado=(
                    "**o parágrafo não sai em município nenhum**: o parser só "
                    "compara `$campo` com um número literal, então a condição "
                    "falha sempre e o texto é descartado"
                ),
                contrato="`valor` referencia o outro campo; a comparação funciona",
            )
        ]

    interpretados = [parsear_frase_operador(t) for t in trechos]
    # Mesma regra do parser atual: um campo sem frase própria herda a frase do
    # último campo que tem uma ("$a e $b for diferente de 0"). O trecho herdado
    # também é guardado, porque é contra ele que a divergência tem de ser
    # provada — comparar contra o trecho vazio acusaria diferença onde os dois
    # parsers concordam.
    compartilhado = next((op for op in reversed(interpretados) if op), None)
    trecho_compartilhado = next(
        (t for t, op in zip(reversed(trechos), reversed(interpretados)) if op), ""
    )

    condicoes: list[dict] = []
    divergencias: list[Divergencia] = []

    for match, trecho, interpretado in zip(matches, trechos, interpretados):
        campo = match.group(1)
        usado = interpretado or compartilhado
        if usado is None:
            divergencias.append(
                Divergencia(
                    tipo="condição não interpretada",
                    linha=linha,
                    trecho=expressao.strip(),
                    legado="o bloco nunca aparece (nenhum operador reconhecido)",
                    contrato="bloco importado **sem regra** (sempre visível) — revisar à mão",
                )
            )
            continue

        op, valor = usado
        # Campos em que NULL não é zero ganham a checagem de presença explícita
        # que hoje é uma lista fixa de nomes dentro do Python.
        if campo in _CAMPOS_NULL_SENSIVEIS:
            condicoes.append({"campo": campo, "op": "existe"})

        condicao = {"campo": campo, "op": op}
        if op != "existe":
            condicao["valor"] = valor
        condicoes.append(condicao)

        trecho_efetivo = trecho if interpretado else trecho_compartilhado
        prova = _provar_divergencia(trecho_efetivo, op, valor)
        if prova:
            divergencias.append(
                Divergencia(
                    tipo="operador corrigido",
                    linha=linha,
                    trecho=f"${campo}{trecho_efetivo.rstrip()}",
                    legado=_descrever_legado(trecho_efetivo),
                    contrato=f"`{op}` {valor}",
                    prova=prova,
                )
            )

    return condicoes, divergencias


def _linhas_gateadas(linhas: list[str], inicio: int) -> list[str]:
    """Linhas que a instrução da posição ``inicio`` controla hoje.

    A máquina de estado atual gateia tudo até a primeira linha em branco — e só
    então volta a `bloco_ativo = True`. Então o alcance real de uma condicional
    simples é este trecho, não o parágrafo que o editor tinha em mente.
    """
    gateadas = []
    for linha in linhas[inicio + 1 :]:
        if not linha.strip():
            break
        gateadas.append(linha.strip())
    return gateadas


def _estrutura_engolida(linhas: list[str], inicio: int) -> list[str]:
    """Linhas *estruturais* no alcance da condicional — títulos de caixa,
    marcadores de gráfico, legendas de figura. Prosa condicional é o objetivo
    do editor; estrutura condicional é vazamento: some do relatório junto com o
    parágrafo, sem que ninguém tenha pedido isso."""
    return [
        linha
        for linha in _linhas_gateadas(linhas, inicio)
        if _CABECALHO_CAIXA.match(linha)
        or _MARCADOR_GRAFICO.match(linha)
        or _LEGENDA_FIGURA.match(linha)
    ]


def _divergencia_vazamento(numero: int, linha: str, engolidas: list[str]) -> Divergencia:
    amostra = "; ".join(f"`{t[:60]}`" for t in engolidas)
    return Divergencia(
        tipo="condicional engole estrutura",
        linha=numero,
        trecho=linha,
        legado=(
            "sem linha em branco depois, a condição continua valendo sobre as "
            f"linhas seguintes e some com elas quando é falsa: {amostra}"
        ),
        contrato="a regra vale só para o bloco a que foi atribuída",
    )


def _divergencia_inerte(numero: int, linha: str) -> Divergencia:
    """A condicional existe no Doc mas não surte efeito no relatório de hoje."""
    return Divergencia(
        tipo="condicional inerte hoje",
        linha=numero,
        trecho=linha,
        legado=(
            "**sem efeito**: a linha em branco logo abaixo reativa o bloco "
            "(`aguardando_fim_de_bloco_simples` em utils/render/placeholders.py), "
            "então o parágrafo sai sempre — junto com as outras variantes da "
            "mesma condição"
        ),
        contrato="a regra passa a valer; só uma das variantes aparece",
    )


def _descrever_legado(trecho: str) -> str:
    operador = _parse_operador_editorial(trecho.casefold())
    if operador is None:
        return "nenhum operador reconhecido — condição sempre falsa"
    from utils.render.placeholders import _OPERADORES_EDITORIAIS

    for padrao, atende in _OPERADORES_EDITORIAIS:
        if atende is operador[0]:
            argumentos = ", ".join(f"{a:g}" for a in operador[1])
            return f"casou `{padrao.pattern}` → aplica com ({argumentos})"
    return "operador reconhecido"


_SUFIXO_PRECISAO_TRECHO = re.compile(r"^:(\d+)\b")


def parsear_trechos(texto: str) -> list[dict]:
    """Texto com ``ns.$campo`` -> lista de trechos ``texto``/``var``."""
    trechos: list[dict] = []
    posicao = 0

    for match in _MARCADOR_CAMPO_CONDICIONAL.finditer(texto):
        if match.start() > posicao:
            trechos.append({"t": "texto", "v": texto[posicao : match.start()]})

        campo = match.group(1)
        prefixo = match.group(0)[: -(len(campo) + 1)].rstrip(".")
        variavel: dict[str, Any] = {
            "t": "var",
            "campo": f"{prefixo}.{campo}" if prefixo else campo,
        }

        fim = match.end()
        sufixo = _SUFIXO_PRECISAO_TRECHO.match(texto[fim:])
        if sufixo:
            variavel["formato"] = {"decimais": int(sufixo.group(1))}
            fim += sufixo.end()

        trechos.append(variavel)
        posicao = fim

    if posicao < len(texto):
        trechos.append({"t": "texto", "v": texto[posicao:]})

    return trechos or [{"t": "texto", "v": texto}]


# Prosa que hoje mora dentro de utils/render/placeholders.py em vez de no Doc.
# O importador a traz para o contrato, que é onde texto editorial deve estar —
# e registra a mudança de lugar como divergência, porque a partir daí quem
# altera essas frases é o operador, não um dev.
_PROSA_RUA_SEM_REGISTRO = (
    "Não foram encontrados registros de pessoas em situação de rua para "
    "demografia.$nm_mun na fonte de dados consultada. Contudo, esse resultado "
    "deve ser interpretado considerando os limites da base de dados utilizada, "
    "não sendo suficiente, por si só, para afastar a presença dessa população "
    "no município."
)
_PROSA_RUA_SO_2022 = (
    "Outro grupo relevante para a caracterização da população municipal é o de "
    "pessoas em situação de rua. Em 2022, demografia.$nm_mun registrava "
    "demografia.$pop_rua_2022 pessoas nessa condição. Entre as famílias em "
    "situação de rua, demografia.$pop_rua_pobreza "
    "(demografia.$pop_rua_pobreza_per)% estavam em situação de pobreza, "
    "demografia.$pop_rua_br (demografia.$pop_rua_br_per)% eram classificadas "
    "como de baixa renda e demografia.$pop_rua_acima_br "
    "(demografia.$pop_rua_acima_br_per)% possuíam renda acima de meio salário "
    "mínimo. Além disso, demografia.$pop_rua_bolsaf_2022 famílias em situação "
    "de rua eram beneficiárias do Bolsa Família. Ainda não há levantamento mais "
    "recente (2026) disponível na fonte consultada para comparação."
)
_INICIO_PARAGRAFO_RUA = re.compile(
    r"(?i)^outro grupo relevante para a caracteriza[cç][aã]o da popula[cç][aã]o municipal"
)


class _Contador:
    """Ids estáveis e legíveis (``corpo-p3``), para o painel endereçar blocos."""

    def __init__(self, prefixo: str) -> None:
        self.prefixo = prefixo
        self.n = 0

    def proximo(self, tipo: str) -> str:
        self.n += 1
        return f"{self.prefixo}-{tipo[0]}{self.n}"


def parsear_blocos(
    texto: str, prefixo_id: str, linha_inicial: int = 1
) -> tuple[list[dict], list[Divergencia]]:
    """Corpo de um bloco marcado -> árvore de blocos + divergências.

    Cada linha não vazia do Doc é um bloco: as linhas em branco são espaçamento
    da exportação, não estrutura (confirmado nos nove documentos do corpus).
    """
    raiz: list[dict] = []
    divergencias: list[Divergencia] = []
    ids = _Contador(prefixo_id)

    caixa: dict | None = None
    grupo: dict | None = None
    regra_pendente: dict | None = None

    def destino() -> list[dict]:
        if grupo is not None:
            return grupo["blocos"]
        if caixa is not None:
            return caixa["blocos"]
        return raiz

    def fechar_grupo() -> None:
        nonlocal grupo
        grupo = None

    def anexar(bloco: dict) -> dict:
        nonlocal regra_pendente
        if regra_pendente is not None:
            bloco["regra"] = regra_pendente
            regra_pendente = None
        else:
            bloco.setdefault("regra", None)
        destino().append(bloco)
        return bloco

    linhas = texto.splitlines()
    for deslocamento, linha in enumerate(linhas):
        numero = linha_inicial + deslocamento
        limpa = linha.strip()
        if not limpa:
            continue

        # Uma instrução editorial seguida de linha em branco não tem efeito
        # hoje: interpretar_blocos_condicionais reativa o bloco na primeira
        # linha vazia (`aguardando_fim_de_bloco_simples`), antes de chegar ao
        # parágrafo que a instrução deveria controlar.
        seguida_de_branco = (
            deslocamento + 1 < len(linhas) and not linhas[deslocamento + 1].strip()
        )

        if _SEM_CONDICAO.match(limpa):
            fechar_grupo()
            regra_pendente = None
            continue

        gini = _CONDICAO_GINI.match(limpa)
        if gini:
            operador_texto, limite_texto = gini.groups()
            op = "menor" if "menor" in operador_texto.casefold() else "maior_igual"
            regra_pendente = {
                "condicoes": [
                    {"campo": "gini_2010", "op": "existe"},
                    {"campo": "gini_2010", "op": op, "valor": _numero(limite_texto)},
                ]
            }
            if seguida_de_branco:
                divergencias.append(_divergencia_inerte(numero, limpa))
            else:
                engolidas = _estrutura_engolida(linhas, deslocamento)
                if engolidas:
                    divergencias.append(
                        _divergencia_vazamento(numero, limpa, engolidas)
                    )
            continue

        instrucao = _INSTRUCAO_CONDICIONAL.match(limpa)
        if instrucao and _MARCADOR_CAMPO_CONDICIONAL.search(instrucao.group(1)):
            condicoes, novas = parsear_condicao(instrucao.group(1), numero)
            divergencias.extend(novas)
            if not condicoes:
                continue
            campos = {c["campo"] for c in condicoes}
            if campos & _CAMPOS_GRUPO_POPULACOES:
                # Abre (ou troca) o grupo indígena/quilombola. No parser atual
                # isto é `bloco_populacoes_ativo`, um booleano global; aqui
                # vira uma seção sem título que carrega a regra.
                fechar_grupo()
                grupo = {
                    "id": ids.proximo("grupo"),
                    "tipo": "secao",
                    "titulo": "",
                    "regra": {"condicoes": condicoes},
                    "blocos": [],
                }
                raiz.append(grupo)
            else:
                regra_pendente = {"condicoes": condicoes}
                # Só o ramo "simples" de interpretar_blocos_condicionais liga o
                # `aguardando_fim_de_bloco_simples`; as condições do grupo
                # indígena/quilombola e as de campo NULL-sensível têm estado
                # próprio e funcionam hoje.
                simples = not (
                    campos & _CAMPOS_SUBORDINADOS
                    or (len(campos) == 1 and campos <= _CAMPOS_NULL_SENSIVEIS)
                )
                if simples and seguida_de_branco:
                    divergencias.append(_divergencia_inerte(numero, limpa))
                elif simples:
                    engolidas = _estrutura_engolida(linhas, deslocamento)
                    if engolidas:
                        divergencias.append(
                            _divergencia_vazamento(numero, limpa, engolidas)
                        )
                if campos & _CAMPOS_SUBORDINADOS and grupo is None:
                    divergencias.append(
                        Divergencia(
                            tipo="condição subordinada sem grupo",
                            linha=numero,
                            trecho=limpa,
                            legado="depende do bloco indígena/quilombola anterior",
                            contrato="importada como regra independente — revisar",
                        )
                    )
            continue
        # Sem "$campo" a linha não é instrução editorial (ex.: "Para saber
        # mais sobre este tema:"); segue como conteúdo normal.

        cabecalho = _CABECALHO_CAIXA.match(limpa)
        if cabecalho:
            fechar_grupo()
            caixa = {
                "id": ids.proximo("caixa"),
                "tipo": "caixa",
                "titulo": cabecalho.group(1).strip(),
                "regra": None,
                "blocos": [],
            }
            raiz.append(caixa)
            continue

        grafico = _MARCADOR_GRAFICO.match(limpa)
        if grafico:
            anexar(
                {
                    "id": ids.proximo("grafico"),
                    "tipo": "grafico",
                    "grafico": grafico.group(1),
                }
            )
            continue

        item = _ITEM_DE_LISTA.match(linha)
        if item:
            anterior = destino()[-1] if destino() else None
            if anterior is not None and anterior.get("tipo") == "lista":
                anterior["itens"].append(parsear_trechos(item.group(1)))
            else:
                anexar(
                    {
                        "id": ids.proximo("lista"),
                        "tipo": "lista",
                        "itens": [parsear_trechos(item.group(1))],
                    }
                )
            continue

        if _LEGENDA_FIGURA.match(limpa):
            anexar(
                {
                    "id": ids.proximo("legenda"),
                    "tipo": "legenda",
                    "conteudo": parsear_trechos(limpa),
                }
            )
            continue

        if (
            _TITULO_DE_SECAO.match(limpa)
            and "$" not in limpa
            and not limpa.endswith((".", ":", "!", "?", ";"))
        ):
            fechar_grupo()
            caixa = None
            # Sem linha em branco antes, render_descricao_tema_html junta o
            # título ao parágrafo anterior e ele sai como texto corrido, sem o
            # <h2>. No contrato o título é um bloco, então o destaque volta.
            if deslocamento > 0 and linhas[deslocamento - 1].strip():
                divergencias.append(
                    Divergencia(
                        tipo="título sem destaque hoje",
                        linha=numero,
                        trecho=limpa,
                        legado=(
                            "sai como `<p class=\"theme-detail-text\">` — o título "
                            "é absorvido pelo parágrafo anterior por falta de uma "
                            "linha em branco no Doc"
                        ),
                        contrato='sai como `<h2 class="theme-detail-heading">`',
                    )
                )
            raiz.append(
                {
                    "id": ids.proximo("secao"),
                    "tipo": "secao",
                    "titulo": limpa,
                    "regra": None,
                    "blocos": [],
                }
            )
            continue

        if _INICIO_PARAGRAFO_RUA.match(limpa):
            divergencias.extend(
                _expandir_paragrafo_rua(limpa, numero, ids, anexar)
            )
            continue

        anexar(
            {
                "id": ids.proximo("paragrafo"),
                "tipo": "paragrafo",
                "conteudo": parsear_trechos(limpa),
            }
        )

    return raiz, divergencias


def _expandir_paragrafo_rua(
    linha: str, numero: int, ids: _Contador, anexar
) -> list[Divergencia]:
    """Transforma o caso "situação de rua" em três blocos com regra explícita.

    Hoje esse parágrafo não tem guarda no Doc: quem decide o que aparece é um
    ``re.match`` sobre a primeira frase, dentro do Python, que também carrega
    duas versões alternativas do texto. As três variantes passam a existir como
    blocos com regra, e o Doc deixa de ter comportamento escondido no código.
    """
    anexar(
        {
            "id": ids.proximo("paragrafo"),
            "tipo": "paragrafo",
            "conteudo": parsear_trechos(linha),
            "regra": {
                "condicoes": [
                    {"campo": "pop_rua_2022", "op": "existe"},
                    {"campo": "pop_rua_2026", "op": "existe"},
                ]
            },
        }
    )
    anexar(
        {
            "id": ids.proximo("paragrafo"),
            "tipo": "paragrafo",
            "conteudo": parsear_trechos(_PROSA_RUA_SO_2022),
            "regra": {
                "condicoes": [
                    {"campo": "pop_rua_2022", "op": "existe"},
                    {"campo": "pop_rua_2026", "op": "nao_existe"},
                ]
            },
        }
    )
    anexar(
        {
            "id": ids.proximo("paragrafo"),
            "tipo": "paragrafo",
            "conteudo": parsear_trechos(_PROSA_RUA_SEM_REGISTRO),
            "regra": {"condicoes": [{"campo": "pop_rua_2022", "op": "nao_existe"}]},
        }
    )
    return [
        Divergencia(
            tipo="prosa que morava no Python",
            linha=numero,
            trecho="parágrafo de população em situação de rua",
            legado=(
                "utils/render/placeholders.py decide por `re.match` na primeira "
                "frase e emite dois parágrafos alternativos escritos em Python"
            ),
            contrato=(
                "três blocos com regra explícita "
                "(`pop_rua_2022`/`pop_rua_2026` × existe/não existe); "
                "o texto passa a ser editável pelo operador"
            ),
        )
    ]


def _linha_de(texto_original: str, fragmento: str) -> int:
    """Linha, no Doc original, onde um bloco extraído começa (1 se não achar)."""
    amostra = fragmento.strip()[:80]
    if not amostra:
        return 1
    posicao = texto_original.find(amostra)
    if posicao < 0:
        return 1
    return texto_original.count("\n", 0, posicao) + 1


def importar_texto(texto: str, macrotema: str) -> ResultadoImportacao:
    """Texto exportado do Doc -> contrato do painel + divergências.

    A moldura é fatiada pela **mesma cadeia extrair_\\*** que
    services/generation.py usa, e na mesma ordem. Reaproveitar o fatiador em vez
    de reimplementá-lo é o que garante que o contrato comece exatamente do
    conteúdo que o relatório de hoje enxerga.
    """
    from utils.external.docs import (
        extrair_descricao_tema,
        extrair_diagnostico_cidade,
        extrair_referencias,
        extrair_relatorio_geral,
        extrair_resumo_cidade,
        extrair_resumo_relatorio,
        extrair_resumo_tema,
        remover_titulos_docs,
    )

    original = texto
    divergencias: list[Divergencia] = []
    moldura: dict[str, Any] = {}

    def fatiar(nome: str, extrator, restante: str) -> str:
        bloco, novo_restante = extrator(restante)
        if bloco:
            blocos, novas = parsear_blocos(bloco, nome, _linha_de(original, bloco))
            divergencias.extend(novas)
            moldura[nome] = {"blocos": blocos}
        return novo_restante

    restante = texto
    restante = fatiar("resumo_tema", extrair_resumo_tema, restante)
    restante = fatiar("relatorio_geral", extrair_relatorio_geral, restante)

    # generation.py descarta o resumo_relatorio do macrotema (a fonte comum é o
    # documento de Características); o importador faz o mesmo para não trazer
    # de volta conteúdo que o relatório já ignora.
    descartado, restante = extrair_resumo_relatorio(restante)
    if descartado:
        divergencias.append(
            Divergencia(
                tipo="bloco descartado",
                linha=_linha_de(original, descartado),
                trecho="resumo_relatorio",
                legado="já é descartado hoje (a fonte é o doc de Características)",
                contrato="não importado",
            )
        )

    referencias, restante = extrair_referencias(restante)
    restante = remover_titulos_docs(
        restante, "Apresentação", "Apresentacao", "Aoresentacao", "Referências"
    )
    restante = fatiar("resumo_cidade", extrair_resumo_cidade, restante)
    restante = fatiar("diagnostico_cidade", extrair_diagnostico_cidade, restante)

    descricao, restante = extrair_descricao_tema(restante)
    corpo_blocos: list[dict] = []
    if descricao:
        corpo_blocos, novas = parsear_blocos(
            descricao, "corpo", _linha_de(original, descricao)
        )
        divergencias.extend(novas)

    # O que sobra depois da cadeia extrair_* não é lixo: services/generation.py
    # o transforma na caixa `fontes_html` do tema (Fontes / Conteúdos
    # relacionados). Vira o slot `fontes`, que a renderização devolve sem
    # marcador para cair exatamente na mesma sobra.
    sobra = restante.strip()
    if sobra:
        blocos_fontes, novas = parsear_blocos(
            sobra, SLOT_FONTES, _linha_de(original, sobra)
        )
        divergencias.extend(novas)
        moldura[SLOT_FONTES] = {"blocos": blocos_fontes}

    moldura["referencias"] = referencias

    contrato = {
        "versao_contrato": 1,
        "macrotema": macrotema,
        "versao": 1,
        "publicado_em": None,
        "publicado_por": None,
        "moldura": moldura,
        "corpo": {"blocos": corpo_blocos},
    }
    return ResultadoImportacao(contrato=contrato, divergencias=divergencias)


def relatorio_markdown(
    resultado: ResultadoImportacao, macrotema: str, origem: str
) -> str:
    """Relatório de divergências, para revisão humana antes de publicar."""
    contrato = resultado.contrato
    n_corpo = len(contrato["corpo"]["blocos"])
    n_regras = _contar_regras(contrato)

    linhas = [
        f"# Importação do Doc — {macrotema}",
        "",
        f"Origem: `{origem}`",
        "",
        "## Resumo",
        "",
        f"- Blocos no corpo: **{n_corpo}** (topo de árvore)",
        f"- Blocos com regra: **{n_regras}**",
        (
            "- Slots de moldura preenchidos: "
            f"**{sorted(k for k in contrato['moldura'] if k != 'referencias')}**"
        ),
        f"- Referências: **{len(contrato['moldura'].get('referencias', []))}**",
        f"- Divergências: **{len(_unicas(resultado.divergencias))}**",
        "",
    ]

    if not resultado.divergencias:
        linhas += ["## Divergências", "", "Nenhuma. O contrato reproduz o Doc.", ""]
        return "\n".join(linhas)

    por_tipo: dict[str, list[Divergencia]] = {}
    vistas: set[tuple] = set()
    for divergencia in resultado.divergencias:
        chave = (divergencia.tipo, divergencia.linha, divergencia.trecho)
        if chave in vistas:
            continue
        vistas.add(chave)
        por_tipo.setdefault(divergencia.tipo, []).append(divergencia)

    linhas += [
        "## Divergências",
        "",
        "Cada item abaixo é um ponto em que o contrato **não** reproduz o",
        "comportamento atual. Divergência prevista não é falha de paridade —",
        "é o que a comparação da Fase 1 deve esperar encontrar.",
        "",
    ]
    for tipo, itens in sorted(por_tipo.items()):
        linhas.append(f"### {tipo} ({len(itens)})")
        linhas.append("")
        linhas.extend(item.como_markdown() for item in itens)
        linhas.append("")

    return "\n".join(linhas)


def _unicas(divergencias: list[Divergencia]) -> list[Divergencia]:
    vistas: set[tuple] = set()
    unicas = []
    for divergencia in divergencias:
        chave = (divergencia.tipo, divergencia.linha, divergencia.trecho)
        if chave not in vistas:
            vistas.add(chave)
            unicas.append(divergencia)
    return unicas


def _contar_regras(contrato: dict) -> int:
    total = 0

    def andar(blocos: list[dict]) -> None:
        nonlocal total
        for bloco in blocos:
            if bloco.get("regra"):
                total += 1
            andar(bloco.get("blocos", []))

    for slot, conteudo in contrato["moldura"].items():
        if slot != "referencias":
            andar(conteudo["blocos"])
    andar(contrato["corpo"]["blocos"])
    return total
