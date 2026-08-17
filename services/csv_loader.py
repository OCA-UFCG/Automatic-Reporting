from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

from utils.data.macrotemas import MACROTEMAS

_CSV_CACHE: dict[str, pd.DataFrame] = {}


def _carregar_csv(csv_source: str | Path) -> pd.DataFrame:
    cache_key = str(csv_source)
    if cache_key in _CSV_CACHE:
        return _CSV_CACHE[cache_key].copy()
    conteudo_bytes = None
    if isinstance(csv_source, str) and csv_source.startswith(("http://", "https://")):
        request = Request(csv_source, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=30) as response:
            conteudo_bytes = response.read()
    for sep in (",", ";"):
        fonte = BytesIO(conteudo_bytes) if conteudo_bytes is not None else csv_source
        try:
            df = pd.read_csv(fonte, sep=sep, engine="c")
            if len(df.columns) > 1:
                break
        except (pd.errors.ParserError, ValueError):
            continue
    _CSV_CACHE[cache_key] = df.copy()
    return df


def get_csv_config_for_macrotema(macrotema: dict[str, str | None]) -> tuple[str | None, str]:
    if macrotema["csv_url"]:
        return macrotema["csv_url"], macrotema["csv_env"]
    return MACROTEMAS["demografia"]["csv_url"], "DEMOGRAFIA_CSV_URL"


def normalizar_colunas_macrotema(df: pd.DataFrame, namespace: str) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(coluna).lstrip("\ufeff").strip() for coluna in df.columns]

    if "nm_mun" not in df.columns and "city" in df.columns:
        df = df.rename(columns={"city": "nm_mun"})

    prefixo = f"{namespace}."
    colunas_renomeadas = {
        coluna: coluna[len(prefixo):]
        for coluna in df.columns
        if coluna.startswith(prefixo)
    }
    if colunas_renomeadas:
        df = df.rename(columns=colunas_renomeadas)

    return df