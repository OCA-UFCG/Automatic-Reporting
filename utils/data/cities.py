import ast

import pandas as pd

from config import CITIES_FILE
from utils.geografia import separar_cidade_uf


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


def _coluna_uf(df: pd.DataFrame) -> str | None:
    for coluna in ("sigla_uf", "uf", "sg_uf"):
        if coluna in df.columns:
            return coluna
    return None


def _resolver_ambiguidade(
    df: pd.DataFrame, matched: pd.DataFrame, mascara: pd.Series, cidade_sem_uf: str, uf_informada: str
) -> pd.DataFrame:
    if matched.empty:
        return matched

    coluna_uf = _coluna_uf(matched)

    # If a UF was given and the data has a UF column, narrow the match to that state.
    if uf_informada and coluna_uf:
        mascara_uf = matched[coluna_uf].astype(str).str.strip().str.upper() == uf_informada
        matched_uf = matched[mascara_uf]
        if not matched_uf.empty:
            return matched_uf

    # Otherwise, check for ambiguity: multiple distinct states matched.
    if coluna_uf:
        states = matched[coluna_uf].astype(str).str.strip().str.upper()
        states = sorted(states[states != ""].unique())
    else:
        serie_cidades = df["nm_mun"].astype(str).str.strip()
        states = sorted(
            serie_cidades[mascara].str.extract(r"\(([A-Za-z]{2})\)$")[0].dropna().unique()
        )
    if len(states) > 1:
        raise ValueError(
            f"Cidade ambígua: '{cidade_sem_uf}' encontrada em {', '.join(states)}. "
            f"Indique o estado, ex: '{cidade_sem_uf} ({states[0]})'"
        )
    return matched


def filtrar_linhas_por_cidade(df: pd.DataFrame, cidade: str) -> pd.DataFrame:
    cidade_informada = cidade.strip()
    serie_cidades = df["nm_mun"].astype(str).str.strip()
    cidade_sem_uf, uf_informada = separar_cidade_uf(cidade_informada)

    # 1. Exact match (case-insensitive) — covers data where nm_mun already embeds "(UF)".
    #    When it doesn't, a query without a UF can still match every state's row here,
    #    so ambiguity still needs to be checked before returning.
    mascara_exata = serie_cidades.str.lower() == cidade_informada.lower()
    if mascara_exata.any():
        return _resolver_ambiguidade(
            df, df[mascara_exata], mascara_exata, cidade_sem_uf, uf_informada
        )

    # 2. Fallback: strip state abbreviations like "(PB)" from nm_mun and match by name alone,
    #    since the CSV's nm_mun is typically plain (no "(UF)").
    serie_sem_uf = serie_cidades.str.replace(r"\s*\([A-Za-z]{2}\)\s*$", "", regex=True)
    mascara_sem_uf = serie_sem_uf.str.lower() == cidade_sem_uf.lower()
    return _resolver_ambiguidade(
        df, df[mascara_sem_uf], mascara_sem_uf, cidade_sem_uf, uf_informada
    )