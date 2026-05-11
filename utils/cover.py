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


def montar_capa_relatorio(linha: dict, gerado_em: datetime) -> dict[str, str]:
    cidade_nome, uf = separar_cidade_uf(linha.get("nm_mun", ""))
    porte = str(linha.get("porte", "médio")).strip().lower() or "médio"
    descricao = (
        f"Município de {porte} porte na microrregião do(a) {cidade_nome}, "
        "bioma Caatinga"
    )
    return {
        "data_extenso": formatar_data_hora_extenso(gerado_em),
        "cidade_nome": cidade_nome,
        "uf": uf,
        "descricao": descricao,
        "populacao": str(linha.get("pop_total", "218.162")),
    }