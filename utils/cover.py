from datetime import datetime

from utils.formatting import coerce_para_float, formatar_numero_ptbr
from utils.geografia import separar_cidade_uf


def formatar_data_extenso(data: datetime) -> str:
    meses = [
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    ]
    return f"{data.day:02d} de {meses[data.month - 1]} de {data.year}"


def formatar_data_hora_extenso(data: datetime) -> str:
    return f"{formatar_data_extenso(data)}, {data.strftime('%H:%M')}"


# Catálogo dos cards do bloco "Panorama de indicadores" da capa de cada
# macrotema, lido do contexto já mesclado em services/generation.py.
#
# `relatorios_auto.vw_indicadores` guarda cada indicador como um quarteto de
# colunas com uma base comum — nm_<base> (rótulo), valor_<base>, fonte_<base>
# e unid_<base>. Rótulo, fonte e unidade vêm de lá, não daqui: antes eram
# repetidos em Python e a cópia já tinha divergido (o card de desertificação
# dizia "Índice de aridez, 2021"; a view diz "Xavier et al. (2019) e OCA").
# Quem edita a view não tem como saber que precisa editar Python também.
#
# Então este catálogo é só quais indicadores entram em cada macrotema e em que
# ordem — uma lista de bases, seguindo o catálogo de big numbers mantido pela
# equipe editorial. O conteúdo do card é todo do banco.

# Teto de casas decimais para os valores lidos da view, que chegam como string
# ("0.467", "419379", "-7305491.00"). É teto, não piso: zeros à direita são
# cortados, então 0,770 vira "0,77" e 0,467 continua "0,467".
_DECIMAIS_VIEW = 3

# A view é consistente no padrão nm_/valor_/fonte_/unid_ com uma exceção: o
# rótulo da população feminina é `nm_pop_feminina`, enquanto valor_, fonte_ e
# unid_ usam `pop_feminino` (compare com `pop_masculina`, regular nas quatro).
# Sem este de/para o card sai da capa em silêncio — o rótulo existe e está
# preenchido, só não no nome que o resto do quarteto anuncia. Remover quando a
# coluna for renomeada no banco.
_ROTULO_IRREGULAR = {"pop_feminino": "nm_pop_feminina"}

# Indicador que só faz sentido quando o grupo existe no município: com
# população zero, "0%" lê como ausência de alfabetização em vez de ausência do
# grupo. Chave = base na view; valor = coluna de população que precisa existir.
_CONDICAO_POR_BASE = {
    "alfabetizada_quilombola": "valor_pop_quilombola",
    "alfabetizada_indigena": "valor_pop_indigena",
}

# Ícone dedicado por base, quando o indicador tem um mais específico do que o
# ícone genérico do macrotema. Recuperado do commit 15a9691 ("feat: new svgs
# for indicators"): aquele commit ainda usava os nomes de coluna completos da
# migração anterior (ex. "sem_instrucao_fund_incomp_per", "qtd_unidades_
# conservacao") e o merge com a reescrita da view (PR #91-like, base curta)
# descartou essas linhas por conflito de estrutura — os SVGs chegaram ao
# Brand.jsx, mas nada aqui os referenciava. Bases não listadas aqui caem no
# ícone do macrotema.
_ICONE_POR_BASE = {
    "pop_indigena": "indigena_alfabetizada",
    "pop_quilombola": "quilombola_alfabetizada",
    "pop_rua": "situacao_rua",
    "fundamental_incom": "fundamental_incompleto",
    "fundamental_com": "fundamental_completo",
    "medio_com": "medio_completo",
    "esgotamento": "esgoto",
    "asd": "desertificacao",
    "asd_avanço": "desertificacao",
    "uc": "unidades_conservacao",
    "uc_pi": "protecao_integral",
    "uc_uso": "uso_sustentavel",
    "uc_area": "area_conservacao",
}

INDICADORES_POR_MACROTEMA: dict[str, tuple[str, ...]] = {
    "demografia": (
        "pop_residente",
        "pop_masculina",
        "pop_feminino",
        "pop_indigena",
        "pop_quilombola",
        "pop_rua",
    ),
    # Educação guarda o valor em `per_<base>` em vez de `valor_<base>`; nm_,
    # fonte_ e unid_ seguem o mesmo padrão dos demais, então rótulo e fonte
    # também vêm da view.
    "educacao": (
        "fundamental_incom",
        "fundamental_com",
        "medio_com",
        "superior_com",
        "alfabetizada_quilombola",
        "alfabetizada_indigena",
    ),
    "saude": (
        "nascidos",
        "mortalidade_infantil",
        "doses",
        "estabelecimento",
        "unidade_basica",
        "posto_saude",
    ),
    # Fora do alinhamento com o catálogo de big numbers, por ora. O catálogo
    # pede PIB, PIB per capita, carga tributária, exportação, importação e
    # balança (todos existem na view), mas `carga_tributaria` é rotulada lá
    # como "Receita tributária municipal", em R$ — valor arrecadado, não a
    # razão sobre o PIB que o nome sugere. Resolver essa divergência com a
    # equipe de dados antes de trocar os cards.
    "economia-renda": ("renda_capita", "gini"),
    "desenvolvimento-social": (
        "idhm",
        "idhm_educacao",
        "idhm_longevidade",
        "idhm_renda",
        "renda_capita",
        "gini",
    ),
    # Os cards de energia (qtd_usinas, potencia_renovavel,
    # potencia_nao_renovavel) saíram: não existe coluna correspondente em
    # vw_indicadores, então nunca tiveram valor desde a migração dela.
    "saneamento": ("esgotamento", "banheiro", "coleta_lixo"),
    # `cisternas`/`abastecimento_humano`/`irrigacao` substituem os antigos
    # `total_2025`/`primeira_agua_qtd`/`segunda_agua_qtd`, que vinham de
    # buscar_tecnologias_acesso_agua. Além de a view já trazer fonte e ano,
    # isso mata o bug do ano fixo: `total_2025` só existia quando o município
    # tinha dado exatamente de 2025 (ver _DECADAS_SERIE_HISTORICA em
    # utils/queries/hidraulica.py). O card de suscetibilidade à escassez saiu
    # junto: não há coluna para ele na view.
    "hidraulica": ("cisternas", "abastecimento_humano", "irrigacao"),
    "meio-ambiente": ("asd", "asd_avanço", "uc", "uc_area", "uc_pi", "uc_uso"),
}


def _formatar_valor_indicador(
    valor: object, decimais: int, prefixo: str = "", sufixo: str = ""
) -> str | None:
    """Formata o valor de um indicador em pt-BR, cortando zeros à direita.

    `decimais` é um teto, não um piso: 0.770 vira "0,77" e 0.443 vira "0,443".
    Isso evita tanto a precisão falsa ("0,770") quanto o arredondamento que
    achataria índices vizinhos. Retorna None quando não há valor a exibir — o
    card é omitido em vez de mostrar "N/D".
    """
    if valor is None:
        return None

    texto_bruto = str(valor).strip()
    if not texto_bruto:
        return None

    texto = formatar_numero_ptbr(valor, decimais=decimais)
    if decimais and "," in texto:
        texto = texto.rstrip("0").rstrip(",")

    return f"{prefixo}{texto}{sufixo}"


def _afixos_da_unidade(unidade: str) -> tuple[str, str]:
    """Deriva prefixo/sufixo do card a partir de `unid_<base>` da view.

    A coluna é texto livre e mistura unidade ("km²", "R$") com descrição
    ("Pessoas residentes", "Óbitos infantis por mil nascidos vivos"). Só as
    formas monetárias e de área/percentual viram marca no número; o resto fica
    apenas no rodapé. Sem isso, "0,05" (domicílios sem banheiro) e "630,03"
    (renda per capita) sairiam sem % e sem R$ — números que enganam.

    ponytail: casamento por texto livre. Se a view ganhar uma coluna de
    unidade padronizada (código em vez de rótulo), trocar por um de/para.
    """
    unidade = unidade.strip()
    if "(%)" in unidade or unidade == "%":
        return "", "%"
    if unidade.startswith("R$"):
        return "R$ ", ""
    if unidade.startswith("US$"):
        return "US$ ", ""
    if unidade.endswith("km²"):
        return "", " km²"
    if "(ha)" in unidade:
        return "", " ha"
    return "", ""


def _card_da_view(
    base: str, contexto: dict, macrotema_icone: str
) -> dict[str, str] | None:
    """Monta um card a partir do quarteto nm_/valor_/fonte_/unid_ da view."""
    condicao = _CONDICAO_POR_BASE.get(base)
    if condicao and not coerce_para_float(contexto.get(condicao), default=0.0):
        return None

    prefixo, sufixo = _afixos_da_unidade(str(contexto.get(f"unid_{base}") or ""))
    # Os indicadores de educação guardam o valor em `per_<base>` em vez de
    # `valor_<base>`; o resto do quarteto (nm_/fonte_/unid_) é idêntico.
    valor_bruto = contexto.get(f"valor_{base}")
    if valor_bruto is None:
        valor_bruto = contexto.get(f"per_{base}")
    valor = _formatar_valor_indicador(
        valor_bruto,
        decimais=_DECIMAIS_VIEW,
        prefixo=prefixo,
        sufixo=sufixo,
    )
    if valor is None:
        return None

    # Sem rótulo não há card: o texto vem da view ou não existe. Preencher
    # daqui esconderia um buraco no banco em vez de corrigi-lo — a ausência do
    # card na capa é o sinal de que falta dado.
    nome = str(contexto.get(_ROTULO_IRREGULAR.get(base, f"nm_{base}")) or "").strip()
    if not nome:
        return None

    return {
        "nome": nome,
        "fonte": str(contexto.get(f"fonte_{base}") or "").strip(),
        "valor": valor,
        "rodape": str(contexto.get(f"unid_{base}") or "").strip(),
        "icone": _ICONE_POR_BASE.get(base, macrotema_icone),
    }


def montar_indicadores_macrotema(
    macrotema_slug: str,
    linha: dict | None = None,
    macrotema_icone: str = "chart",
) -> list[dict[str, str]]:
    """Monta os cards de indicador de um macrotema a partir do contexto.

    `linha` é o contexto já mesclado do relatório, que inclui as colunas de
    `relatorios_auto.vw_indicadores`. Indicadores sem valor no banco são
    omitidos: um card a menos é preferível a um número inventado.
    """
    contexto = linha or {}
    cards: list[dict[str, str]] = []

    for base in INDICADORES_POR_MACROTEMA.get(macrotema_slug, ()):
        card = _card_da_view(base, contexto, macrotema_icone)
        if card is not None:
            cards.append(card)

    return cards


def montar_score_macrotema(linha: dict) -> dict[str, str]:
    def primeiro_valor(*chaves: str, fallback: str = "N/D") -> str:
        for chave in chaves:
            valor = linha.get(chave)
            if valor is not None and str(valor).strip():
                return str(valor)
        return fallback

    return {
        "valor": primeiro_valor("score_geral", "score", fallback="3,66"),
        "maximo": primeiro_valor("score_maximo", fallback="5"),
        "status": primeiro_valor(
            "score_status",
            fallback="Acima da média nacional",
        ),
        "descricao": (
            "Score calculado a partir dos indicadores presentes em cada um "
            "dos temas e sua relação com média nacional."
        ),
        "texto_apoio": primeiro_valor(
            "score_texto_apoio", "texto_score", fallback=""
        ),
    }


def montar_capa_relatorio(
    linha: dict,
    gerado_em: datetime,
    macrotema_nome: str = "Saúde",
    macrotema_slug: str = "",
) -> dict[str, object]:
    cidade_nome, uf = separar_cidade_uf(linha.get("nm_mun", ""))
    if not uf:
        uf = str(
            linha.get("sigla_uf")
            or linha.get("uf")
            or linha.get("sg_uf")
            or ""
        ).strip().upper()
    macrotema_normalizado = macrotema_nome.casefold()
    macrotema_icone = "chart"
    macrotema_cor = ""
    if macrotema_slug:
        from utils.data.macrotemas import MACROTEMAS
        dados_macrotema = MACROTEMAS.get(macrotema_slug, {})
        macrotema_icone = dados_macrotema.get("icone", "chart")
        macrotema_cor = dados_macrotema.get("cor", "")
    else:
        if "saúde" in macrotema_normalizado or "saude" in macrotema_normalizado:
            macrotema_icone = "health"
            macrotema_cor = "#E5333F"
        elif "educa" in macrotema_normalizado:
            macrotema_icone = "book"
            macrotema_cor = "#FFD65A"
        elif "demo" in macrotema_normalizado:
            macrotema_icone = "people"
            macrotema_cor = "#D65384"
        elif "desenvolvimento" in macrotema_normalizado or "social" in macrotema_normalizado:
            macrotema_icone = "social"
            macrotema_cor = "#7C46E1"
        elif "economia" in macrotema_normalizado or "renda" in macrotema_normalizado:
            macrotema_icone = "dollar"
            macrotema_cor = "#F79339"
        elif "saneamento" in macrotema_normalizado or "infraestrutura" in macrotema_normalizado:
            macrotema_icone = "wrench"
            macrotema_cor = "#001A72"
        elif "meio" in macrotema_normalizado or "ambiente" in macrotema_normalizado:
            macrotema_icone = "leaf"
            macrotema_cor = "#B0CC41"
        elif "hídrica" in macrotema_normalizado or "hidrica" in macrotema_normalizado or "segurança" in macrotema_normalizado:
            macrotema_icone = "water"
            macrotema_cor = "#35B2DB"
        elif "instrumentos" in macrotema_normalizado or "sudene" in macrotema_normalizado:
            macrotema_icone = "chart"
            macrotema_cor = "#018F39"

    def primeiro_valor(*chaves: str, fallback: str = "N/D") -> str:
        for chave in chaves:
            valor = linha.get(chave)
            if valor is not None and str(valor).strip():
                return str(valor)
        return fallback

    def numero_formatado(*chaves: str, decimais: int = 0, fallback: str = "N/D") -> str:
        for chave in chaves:
            valor = linha.get(chave)
            if valor is None or not str(valor).strip():
                continue
            return formatar_numero_ptbr(valor, decimais=decimais)
        return fallback

    return {
        "data_extenso": formatar_data_extenso(gerado_em),
        "data_hora_extenso": formatar_data_hora_extenso(gerado_em),
        "cidade_nome": cidade_nome,
        "uf": uf,
        "inicio_relatorio": "Dados municipais reunidos em uma única plataforma",
        "inicio_relatorio_subtitulo": "",
        "introducao": "",
        "introducao_html": [],
        "relatorio_geral": "",
        "relatorio_geral_html": [],
        "resumo_relatorio": "",
        "resumo_relatorio_html": [],
        "resumo_cidade": "",
        "resumo_cidade_html": [],
        "diagnostico_cidade": "",
        "diagnostico_cidade_html": [],
        "mapa_principal": "",
        "macrotema": {
            "nome": macrotema_nome,
            "icone": macrotema_icone,
            "status": primeiro_valor(
                "macrotema_status",
                "status_macrotema",
                fallback="Muito acima da média nacional",
            ),
         "resumo": primeiro_valor("resumo_tema", fallback=""),
         "cor": macrotema_cor,
         "score": montar_score_macrotema(linha),
         "descricao": "",
            "descricao_paragrafos": [],
        },
        "score": montar_score_macrotema(linha),
        "metricas": [
            {
                "rotulo": "Área territorial",
                "valor": numero_formatado(
                    "area_territorial", "area", "area_km2", decimais=1
                ),
                "sufixo": "Km²",
                "fonte": "Censo demográfico 2022",
                "caption": "Tamanho do território",
                "icone": "area",
            },
            {
                "rotulo": "População",
                "valor": numero_formatado("pop_total", fallback="N/D"),
                "sufixo": "",
                "fonte": "Censo demográfico 2022",
                "caption": "Número de residentes",
                "icone": "populacao",
            },
            {
                "rotulo": "Região geográfica imediata",
                "valor": primeiro_valor("rgi", "regiao_imediata", "nome_rgi"),
                "sufixo": "",
                "fonte": "IBGE 2017",
                "caption": "Região geográfica imediata",
                "icone": "rgi",
            },
            {
                "rotulo": "Criação do município",
                "valor": primeiro_valor("instalacao", "data_instalacao", "ano_instalacao"),
                "sufixo": "",
                "fonte": "IBGE",
                "caption": "Lei Provincial nº 11",
                "icone": "criacao",
            },
        ],
    }
