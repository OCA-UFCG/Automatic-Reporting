import os
import time
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pandas as pd

from utils.data.macrotemas import MACROTEMAS

_CACHE_TTL_SECONDS = 3600
_CSV_CACHE: dict[str, dict] = {}


def _parse_csv(csv_source: str | Path, conteudo_bytes: bytes | None) -> pd.DataFrame:
    df = None
    for sep in (",", ";"):
        fonte = BytesIO(conteudo_bytes) if conteudo_bytes is not None else csv_source
        try:
            df = pd.read_csv(fonte, sep=sep, engine="c")
            if len(df.columns) > 1:
                break
        except (pd.errors.ParserError, ValueError):
            continue
    if df is None:
        raise ValueError("Unable to parse CSV with separators ',;'")
    return df


def _baixar_csv(csv_source: str, registro: dict | None) -> tuple[int, bytes, object]:
    headers = {"User-Agent": "Mozilla/5.0"}
    if registro:
        if registro.get("last_modified"):
            headers["If-Modified-Since"] = registro["last_modified"]
        if registro.get("etag"):
            headers["If-None-Match"] = registro["etag"]
    request = Request(csv_source, headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, response.read(), response.headers
    except HTTPError as exc:
        if exc.code == 304:
            return 304, b"", exc.headers
        raise


def _carregar_csv_http(
    csv_source: str, cache_key: str, registro: dict | None, agora: float
) -> pd.DataFrame:
    if registro and agora - registro["fetched_at"] < _CACHE_TTL_SECONDS:
        return registro["df"].copy()
    status, conteudo_bytes, response_headers = _baixar_csv(csv_source, registro)
    if status == 304:
        registro["fetched_at"] = agora
        return registro["df"].copy()
    df = _parse_csv(csv_source, conteudo_bytes)
    _CSV_CACHE[cache_key] = {
        "df": df.copy(),
        "fetched_at": agora,
        "last_modified": response_headers.get("Last-Modified") or (registro or {}).get("last_modified"),
        "etag": response_headers.get("ETag") or (registro or {}).get("etag"),
    }
    return df


def _carregar_csv_local(
    csv_source: str | Path, cache_key: str, registro: dict | None, agora: float
) -> pd.DataFrame:
    mtime = os.path.getmtime(csv_source)
    if registro:
        if mtime == registro["mtime"]:
            registro["fetched_at"] = agora
            return registro["df"].copy()
    df = _parse_csv(csv_source, None)
    _CSV_CACHE[cache_key] = {"df": df.copy(), "fetched_at": agora, "mtime": mtime}
    return df


def carregar_csv(csv_source: str | Path) -> pd.DataFrame:
    cache_key = str(csv_source)
    registro = _CSV_CACHE.get(cache_key)
    agora = time.time()
    if isinstance(csv_source, str) and csv_source.startswith(("http://", "https://")):
        return _carregar_csv_http(csv_source, cache_key, registro, agora)
    return _carregar_csv_local(csv_source, cache_key, registro, agora)


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