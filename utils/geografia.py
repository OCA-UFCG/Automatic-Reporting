def separar_cidade_uf(nome_municipio: str) -> tuple[str, str]:
    nome = str(nome_municipio).strip()
    if nome.endswith(")") and "(" in nome:
        cidade, uf = nome.rsplit("(", 1)
        return cidade.strip(), uf.rstrip(")").strip().upper()
    return nome, ""


def resolver_nome_uf(linha: dict) -> tuple[str, str]:
    nome_cidade, uf = separar_cidade_uf(linha.get("nm_mun", ""))
    if not uf:
        uf = str(
            linha.get("sigla_uf") or linha.get("uf") or linha.get("sg_uf") or ""
        ).strip().upper()
    return nome_cidade, uf