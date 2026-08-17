def separar_cidade_uf(nome_municipio: str) -> tuple[str, str]:
    nome = str(nome_municipio).strip()
    if nome.endswith(")") and "(" in nome:
        cidade, uf = nome.rsplit("(", 1)
        return cidade.strip(), uf.rstrip(")").strip().upper()
    return nome, ""