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


def montar_capa_relatorio(linha: dict, gerado_em: datetime) -> dict[str, object]:
    cidade_nome, uf = separar_cidade_uf(linha.get("nm_mun", ""))

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
