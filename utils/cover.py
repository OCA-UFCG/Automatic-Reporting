from datetime import datetime

from utils.formatting import formatar_numero_ptbr
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
# macrotema. Cada entrada aponta para uma coluna de
# `relatorios_auto.vw_indicadores` (ver utils/queries/indicadores.py), lida do
# contexto já mesclado em services/generation.py. Antes disso os cards traziam
# score fixo no código ("4/5") ou "N/D"; a fonte agora é sempre o banco.
#
# Campos: coluna (nome na view), nome (rótulo), fonte (linha pequena do card),
# rodape (texto do rodapé), decimais (máximo, zeros à direita são cortados),
# prefixo/sufixo (unidade) e icone (opcional; cai no ícone do macrotema).
INDICADORES_POR_MACROTEMA: dict[str, tuple[dict[str, object], ...]] = {
    "demografia": (
        {
            "coluna": "pop_quilombola_2022",
            "nome": "População quilombola",
            "fonte": "Censo demográfico 2022",
            "rodape": "Pessoas residentes em domicílios quilombolas",
            "decimais": 0,
            "icone": "people",
        },
        {
            "coluna": "pop_quilombola_per_2022",
            "nome": "Participação da população quilombola",
            "fonte": "Censo demográfico 2022",
            "rodape": "Percentual sobre a população residente",
            "decimais": 2,
            "sufixo": "%",
            "icone": "people",
        },
    ),
    "educacao": (
        {
            "coluna": "nao_alfabetizados_15_mais",
            "nome": "Pessoas não alfabetizadas (15 anos ou mais)",
            "fonte": "Censo demográfico 2022",
            "rodape": "População de 15 anos ou mais não alfabetizada",
            "decimais": 0,
            "icone": "book",
        },
        {
            "coluna": "reducao_nao_alfabetizados_2010_2022",
            "nome": "Redução de não alfabetizados (2010–2022)",
            "fonte": "Censo demográfico 2010 e 2022",
            "rodape": "Diferença de não alfabetizados entre os dois censos",
            "decimais": 0,
            "icone": "book",
        },
        {
            "coluna": "sem_instrucao_fund_incomp_per",
            "nome": "Sem instrução ou fundamental incompleto",
            "fonte": "Censo demográfico 2010",
            "rodape": "Participação no total por grau de instrução",
            "decimais": 2,
            "sufixo": "%",
            "icone": "book",
        },
        {
            "coluna": "fund_comp_medio_incomp_per",
            "nome": "Fundamental completo ou médio incompleto",
            "fonte": "Censo demográfico 2010",
            "rodape": "Participação no total por grau de instrução",
            "decimais": 2,
            "sufixo": "%",
            "icone": "book",
        },
        {
            "coluna": "medio_comp_superior_incomp_per",
            "nome": "Médio completo ou superior incompleto",
            "fonte": "Censo demográfico 2010",
            "rodape": "Participação no total por grau de instrução",
            "decimais": 2,
            "sufixo": "%",
            "icone": "book",
        },
        {
            "coluna": "superior_completo_per",
            "nome": "Superior completo",
            "fonte": "Censo demográfico 2010",
            "rodape": "Participação no total por grau de instrução",
            "decimais": 2,
            "sufixo": "%",
            "icone": "book",
        },
    ),
    # `rendimento_medio_ocupados` é, na definição da view, o mesmo
    # max(renda_per_capita) de `renda_per_capita_2010`. Exibir os dois repetiria
    # o número no card ao lado, então só a renda per capita entra aqui.
    "economia-renda": (
        {
            "coluna": "renda_per_capita_2010",
            "nome": "Renda per capita",
            "fonte": "Atlas Brasil / PNUD, 2010",
            "rodape": "Renda média mensal por habitante",
            "decimais": 2,
            "prefixo": "R$ ",
        },
        {
            "coluna": "indice_gini_2010",
            "nome": "Índice de Gini",
            "fonte": "Atlas Brasil / PNUD, 2010",
            "rodape": "Concentração de renda: 0 é igualdade total, 1 é desigualdade máxima",
            "decimais": 2,
        },
    ),
    "desenvolvimento-social": (
        {
            "coluna": "idhm_2010",
            "nome": "IDHM",
            "fonte": "Atlas Brasil / PNUD, 2010",
            "rodape": "Índice de Desenvolvimento Humano Municipal",
            "decimais": 3,
        },
        {
            "coluna": "renda_per_capita_2010",
            "nome": "Renda per capita",
            "fonte": "Atlas Brasil / PNUD, 2010",
            "rodape": "Renda média mensal por habitante",
            "decimais": 2,
            "prefixo": "R$ ",
        },
        {
            "coluna": "indice_gini_2010",
            "nome": "Índice de Gini",
            "fonte": "Atlas Brasil / PNUD, 2010",
            "rodape": "Concentração de renda: 0 é igualdade total, 1 é desigualdade máxima",
            "decimais": 2,
        },
    ),
    "saneamento": (
        {
            "coluna": "aumento_domicilios_rede_esgoto_2010_2022",
            "nome": "Aumento de domicílios com rede de esgoto (2010–2022)",
            "fonte": "Censo demográfico 2010 e 2022",
            "rodape": "Domicílios ligados à rede geral ou pluvial",
            "decimais": 0,
        },
        {
            "coluna": "qtd_usinas",
            "nome": "Usinas de geração de energia",
            "fonte": "ANEEL / SIGA",
            "rodape": "Usinas em operação no município",
            "decimais": 0,
        },
        {
            "coluna": "potencia_renovavel",
            "nome": "Potência instalada renovável",
            "fonte": "ANEEL / SIGA",
            "rodape": "Solar, eólica, biomassa e hídrica",
            "decimais": 0,
            "sufixo": " kW",
        },
        {
            "coluna": "potencia_nao_renovavel",
            "nome": "Potência instalada não renovável",
            "fonte": "ANEEL / SIGA",
            "rodape": "Fontes fósseis",
            "decimais": 0,
            "sufixo": " kW",
        },
    ),
    "hidraulica": (
        {
            "coluna": "indice_suscetibilidade_escassez_hidrica",
            "nome": "Índice de suscetibilidade à escassez hídrica",
            "fonte": "Ameaça de escassez hídrica, 2020",
            "rodape": "Quanto maior o índice, maior a suscetibilidade",
            "decimais": 2,
            "icone": "water",
        },
    ),
    "meio-ambiente": (
        {
            "coluna": "area_suscetivel_desertificacao",
            "nome": "Área suscetível à desertificação",
            "fonte": "Índice de aridez, 2021",
            "rodape": "Área do município em classes de aridez suscetíveis",
            "decimais": 2,
            "sufixo": " km²",
        },
        # Recorte estadual: na view esse avanço é calculado por sigla_uf, não por
        # município. O rótulo precisa deixar isso explícito.
        {
            "coluna": "avanco_area_suscetivel_desertificacao_1991_2021",
            "nome": "Avanço da área suscetível à desertificação no estado (1991–2021)",
            "fonte": "Índice de aridez, 1991 e 2021",
            "rodape": "Variação da área suscetível no estado, não no município",
            "decimais": 2,
            "sufixo": " km²",
        },
        {
            "coluna": "qtd_unidades_conservacao",
            "nome": "Unidades de conservação",
            "fonte": "CNUC / MMA",
            "rodape": "Unidades de conservação no município",
            "decimais": 0,
        },
        {
            "coluna": "qtd_grupo_protecao_integral",
            "nome": "Unidades de proteção integral",
            "fonte": "CNUC / MMA",
            "rodape": "Grupo de manejo de proteção integral",
            "decimais": 0,
        },
        {
            "coluna": "qtd_grupo_uso_sustentavel",
            "nome": "Unidades de uso sustentável",
            "fonte": "CNUC / MMA",
            "rodape": "Grupo de manejo de uso sustentável",
            "decimais": 0,
        },
        {
            "coluna": "area_unidades_conservacao_ha",
            "nome": "Área em unidades de conservação",
            "fonte": "CNUC / MMA",
            "rodape": "Área total protegida no município",
            "decimais": 2,
            "sufixo": " ha",
        },
    ),
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

    for spec in INDICADORES_POR_MACROTEMA.get(macrotema_slug, ()):
        valor = _formatar_valor_indicador(
            contexto.get(spec["coluna"]),
            decimais=int(spec.get("decimais", 0)),
            prefixo=str(spec.get("prefixo", "")),
            sufixo=str(spec.get("sufixo", "")),
        )
        if valor is None:
            continue

        cards.append(
            {
                "nome": str(spec["nome"]),
                "fonte": str(spec["fonte"]),
                "valor": valor,
                "rodape": str(spec.get("rodape", "")),
                "icone": str(spec.get("icone") or macrotema_icone),
            }
        )

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
