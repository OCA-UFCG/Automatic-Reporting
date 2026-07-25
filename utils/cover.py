import re
from datetime import datetime


def formatar_data_extenso(data: datetime) -> str:
    meses = [
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    ]
    return f"{data.day:02d} de {meses[data.month - 1]} de {data.year}"


def formatar_data_hora_extenso(data: datetime) -> str:
    return f"{formatar_data_extenso(data)}, {data.strftime('%H:%M')}"


def separar_cidade_uf(nome_municipio: str) -> tuple[str, str]:
    match = re.match(r"^(.*?)\s*\(([A-Za-z]{2})\)\s*$", str(nome_municipio).strip())
    if match:
        return match.group(1).strip(), match.group(2).upper()
    return str(nome_municipio).strip(), ""


def montar_capa_relatorio(
    linha: dict,
    gerado_em: datetime,
    macrotema_nome: str = "Saúde",
) -> dict[str, object]:
    cidade_nome, uf = separar_cidade_uf(linha.get("nm_mun", ""))
    macrotema_normalizado = macrotema_nome.casefold()
    macrotema_icone = "chart"
    if "saúde" in macrotema_normalizado or "saude" in macrotema_normalizado:
        macrotema_icone = "health"
    elif "educa" in macrotema_normalizado:
        macrotema_icone = "book"
    elif "demo" in macrotema_normalizado:
        macrotema_icone = "people"
    elif "economia" in macrotema_normalizado or "renda" in macrotema_normalizado:
        macrotema_icone = "chart"
    elif "saneamento" in macrotema_normalizado:
        macrotema_icone = "drop"
    elif "hídrica" in macrotema_normalizado or "hidrica" in macrotema_normalizado:
        macrotema_icone = "water"

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
        "cidade_nome": cidade_nome,
        "uf": uf,
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
            "resumo": primeiro_valor(
                "resumo_tema",
                fallback=(
                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                    "Integer gravida mi ut vestibulum vestibulum. Donec a "
                    "fermentum est. Aliquam efficitur et purus at facilisis. "
                    "Cras ultricies metus lacus. Duis dictum finibus turpis, "
                    "quis euismod lorem vehicula quis. Quisque felis ante."
                ),
            ),
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
                "score_texto_apoio",
                "texto_score",
                fallback=(
                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                    "Integer gravida mi ut vestibulum vestibulum. Donec a "
                    "fermentum est. Aliquam efficitur et purus at facilisis. "
                    "Cras ultricies metus lacus. Duis dictum finibus turpis, "
                    "quis euismod lorem vehicula quis. Quisque felis ante."
                ),
            ),
        },
        "metricas": [
            {
                "rotulo": "Área territorial",
                "valor": primeiro_valor("area_territorial", "area", "area_km2"),
                "sufixo": "Km²",
                "fonte": "Censo demográfico 2022",
                "caption": "Tamanho do território",
            },
            {
                "rotulo": "População",
                "valor": primeiro_valor("pop_total", fallback="N/D"),
                "sufixo": "",
                "fonte": "Censo demográfico 2022",
                "caption": "Número de residentes",
            },
            {
                "rotulo": "IDH",
                "valor": primeiro_valor("idh", "idhm"),
                "sufixo": "",
                "fonte": "IBGE 2023",
                "caption": "Índice de desenvolvimento humano",
            },
            {
                "rotulo": "PIB",
                "valor": primeiro_valor("pib", "pib_total"),
                "sufixo": "",
                "fonte": "IBGE 2023",
                "caption": "Produto Interno Bruto",
            },
        ],
    }
