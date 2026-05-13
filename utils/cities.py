import ast
import re
import pandas as pd

from config import CITIES_FILE


def carregar_cidades() -> list[str]:
    if not CITIES_FILE.exists():
        return []

    conteudo = CITIES_FILE.read_text(encoding="utf-8").strip()
    if not conteudo:
        return []

    try:
        cidades = ast.literal_eval(conteudo)
        if isinstance(cidades, list):
            return [str(cidade).strip() for cidade in cidades if str(cidade).strip()]
    except (ValueError, SyntaxError):
        pass

    return [linha.strip() for linha in conteudo.splitlines() if linha.strip()]


def normalizar_nome_cidade(cidade: str) -> str:
    return re.sub(r"\s*\([A-Za-z]{2}\)\s*$", "", cidade).strip()


def filtrar_linhas_por_cidade(df: pd.DataFrame, cidade: str) -> pd.DataFrame:
    cidade_informada = cidade.strip()
    serie_cidades = df["nm_mun"].astype(str).str.strip()
    # 1. Exact match (case-insensitive)
    mascara_exata = serie_cidades.str.lower() == cidade_informada.lower()
    if mascara_exata.any():
        return df[mascara_exata]
    # 2. Fallback: strip state abbreviations like "(PB)" and match
    cidade_sem_uf = normalizar_nome_cidade(cidade_informada)
    serie_sem_uf = serie_cidades.str.replace(r"\s*\([A-Za-z]{2}\)\s*$", "", regex=True)
    mascara_sem_uf = serie_sem_uf.str.lower() == cidade_sem_uf.lower()
    matched = df[mascara_sem_uf]
    if matched.empty:
        return matched
    # 3. Check for ambiguity: multiple states matched
    states = serie_cidades[mascara_sem_uf].str.extract(r"\(([A-Za-z]{2})\)$")[0].dropna().unique()
    if len(states) > 1:
        raise ValueError(
            f"Cidade ambígua: '{cidade_informada}' encontrada em {', '.join(sorted(states))}. "
            f"Indique o estado, ex: '{cidade_sem_uf} ({states[0]})'"
        )
    return matched