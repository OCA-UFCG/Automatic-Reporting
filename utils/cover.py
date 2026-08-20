from datetime import datetime

from utils.geografia import separar_cidade_uf


def formatar_data_extenso(data: datetime) -> str:
    meses = [
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    ]
    return f"{data.day:02d} de {meses[data.month - 1]} de {data.year}"


def formatar_data_hora_extenso(data: datetime) -> str:
    return f"{formatar_data_extenso(data)}, {data.strftime('%H:%M')}"


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

    def montar_indicadores_macrotema() -> list[dict[str, str]]:
        fonte = "Censo demográfico 2022"
        if "saúde" in macrotema_normalizado or "saude" in macrotema_normalizado:
            return [
                {
                    "nome": "Estabelecimentos de saúde",
                    "fonte": fonte,
                    "score": "4/5",
                    "classe": "very-high",
                    "icone": "hospital",
                },
                {
                    "nome": "Taxa de Mortalidade Infantil",
                    "fonte": fonte,
                    "score": "2/5",
                    "classe": "low",
                    "icone": "health",
                },
                {
                    "nome": "Doses Aplicadas",
                    "fonte": fonte,
                    "score": "3/5",
                    "classe": "high",
                    "icone": "vaccine",
                },
                {
                    "nome": "Postos de saúde",
                    "fonte": fonte,
                    "score": "1/5",
                    "classe": "very-low",
                    "icone": "hospital",
                },
                {
                    "nome": "Nascidos vivos",
                    "fonte": fonte,
                    "score": "4/5",
                    "classe": "very-high",
                    "icone": "birth",
                },
                {
                    "nome": "Número de hospitais",
                    "fonte": fonte,
                    "score": "3/5",
                    "classe": "high",
                    "icone": "shield",
                },
            ]

        indicadores_por_tema = {
            "demografia": [
                "População residente",
                "Variação populacional",
                "Sexo, idade, cor/raça",
            ],
            "educa": [
                "Taxa de alfabetização",
                "Grau de instrução",
                "Analfabetismo",
            ],
            "economia": [
                "PIB total e per capita",
                "Composição setorial do VAB",
                "Comércio exterior",
            ],
            "renda": [
                "PIB total e per capita",
                "Composição setorial do VAB",
                "Comércio exterior",
            ],
            "saneamento": [
                "Coleta de lixo",
                "Esgotamento sanitário",
                "Acesso à energia elétrica",
            ],
            "hidrica": [
                "Cisternas",
                "Distribuição por finalidade",
                "Evolução temporal",
            ],
            "hídrica": [
                "Cisternas",
                "Distribuição por finalidade",
                "Evolução temporal",
            ],
        }

        nomes = ["Indicador 1", "Indicador 2", "Indicador 3"]
        for chave, indicadores in indicadores_por_tema.items():
            if chave in macrotema_normalizado:
                nomes = indicadores
                break

        return [
            {
                "nome": nome,
                "fonte": fonte,
                "score": "N/D",
                "classe": "unknown",
                "icone": macrotema_icone,
            }
            for nome in nomes
        ]

    def primeiro_valor(*chaves: str, fallback: str = "N/D") -> str:
        for chave in chaves:
            valor = linha.get(chave)
            if valor is not None and str(valor).strip():
                return str(valor)
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
         "score": {
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
         },
         "descricao": "",
            "descricao_paragrafos": [],
            "indicadores": montar_indicadores_macrotema(),
        },
        "score": {
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
        },
        "metricas": [
            {
                "rotulo": "Área territorial",
                "valor": primeiro_valor("area_territorial", "area", "area_km2"),
                "sufixo": "Km²",
                "fonte": "Censo demográfico 2022",
                "caption": "Tamanho do território",
                "icone": "area",
            },
            {
                "rotulo": "População",
                "valor": primeiro_valor("pop_total", fallback="N/D"),
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
