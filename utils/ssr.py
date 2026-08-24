from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import subprocess
import time
from collections import OrderedDict
from pathlib import Path

import httpx

BASE_DIR = Path(__file__).resolve().parent.parent
SSR_BUNDLE = BASE_DIR / "report" / "ssr-dist" / "entry.js"
SSR_SERVER_BUNDLE = BASE_DIR / "report" / "ssr-dist" / "server.js"
SSR_PORT = int(os.environ.get("SSR_PORT", "3001"))

_server_process: subprocess.Popen | None = None

_SSR_CACHE_MAX = int(os.environ.get("SSR_CACHE_MAX", "64"))
_SSR_CACHE_TTL = int(os.environ.get("SSR_CACHE_TTL", "3600"))
_ssr_cache: OrderedDict[str, tuple[float, str]] = OrderedDict()
_ssr_cache_hits = 0
_ssr_cache_misses = 0


def normalizar_para_json(valor):
    """Converte valores de dados ausentes/não finitos em JSON ``null``."""
    if isinstance(valor, dict):
        return {chave: normalizar_para_json(item) for chave, item in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [normalizar_para_json(item) for item in valor]
    if isinstance(valor, float):
        return valor if math.isfinite(valor) else None

    from decimal import Decimal
    if isinstance(valor, Decimal):
        try:
            float_val = float(valor)
            return float_val if math.isfinite(float_val) else None
        except (ValueError, OverflowError):
            return None

    # Scalars NumPy/Pandas podem não ser aceitos pelo encoder JSON. ``item``
    # converte esses valores para o tipo Python correspondente; NaN/Inf são
    # tratados na chamada recursiva seguinte.
    item = getattr(valor, "item", None)
    if callable(item):
        try:
            convertido = item()
        except (TypeError, ValueError):
            pass
        else:
            if convertido is not valor:
                return normalizar_para_json(convertido)

    # ``pandas.NA`` não permite conversão para bool e não possui um ``item``
    # útil. A comparação pelo nome evita importar pandas nesta camada.
    if type(valor).__name__ == "NAType":
        return None
    return valor


def _bundle_path() -> Path:
    """Return the built SSR server bundle, falling back to the one-shot entry."""
    if SSR_SERVER_BUNDLE.exists():
        return SSR_SERVER_BUNDLE
    return SSR_BUNDLE


def start_server() -> subprocess.Popen:
    global _server_process

    bundle = _bundle_path()
    if not bundle.exists():
        raise RuntimeError(
            f"SSR bundle not found at {bundle}. "
            "Run 'npm run build -w report' first."
        )

    env = os.environ.copy()
    env["SSR_PORT"] = str(SSR_PORT)

    _server_process = subprocess.Popen(
        ["node", str(bundle)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    return _server_process


def stop_server() -> None:
    global _server_process
    if _server_process is not None:
        _server_process.terminate()
        try:
            _server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_process.kill()
        _server_process = None


def _normalizar_para_cache(valor):
    if isinstance(valor, dict):
        return {
            k: (v.split(",")[0] if k == "data_hora_extenso" and isinstance(v, str) else _normalizar_para_cache(v))
            for k, v in valor.items()
            if k not in {"hora_relatorio", "hora_geracao"}
        }
    if isinstance(valor, list):
        return [_normalizar_para_cache(item) for item in valor]
    return valor


def _ssr_cache_key(props: dict) -> str:
    payload = _normalizar_para_cache(props)
    serializado = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(serializado.encode("utf-8")).hexdigest()


def _ssr_cache_get(key: str) -> str | None:
    item = _ssr_cache.get(key)
    if item is None:
        return None
    timestamp, html = item
    if time.time() - timestamp > _SSR_CACHE_TTL:
        _ssr_cache.pop(key, None)
        return None
    _ssr_cache.move_to_end(key)
    return html


def _ssr_cache_put(key: str, html: str) -> None:
    _ssr_cache[key] = (time.time(), html)
    _ssr_cache.move_to_end(key)
    while len(_ssr_cache) > _SSR_CACHE_MAX:
        _ssr_cache.popitem(last=False)


async def render_react_ssr(props: dict, timeout: int = 30) -> str:
    global _ssr_cache_hits, _ssr_cache_misses

    props = normalizar_para_json(props)
    key = _ssr_cache_key(props)
    cached = _ssr_cache_get(key)
    if cached is not None:
        _ssr_cache_hits += 1
        return cached

    _ssr_cache_misses += 1

    bundle = _bundle_path()

    if not bundle.exists():
        raise RuntimeError(
            f"SSR bundle not found at {bundle}. "
            "Run 'npm run build -w report' first."
        )

    if bundle == SSR_SERVER_BUNDLE:
        html = await _render_via_http(props, timeout)
    else:
        html = await _render_via_subprocess(props, timeout)

    _ssr_cache_put(key, html)
    return html


async def _render_via_http(props: dict, timeout: int = 30) -> str:
    url = f"http://127.0.0.1:{SSR_PORT}/render"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=props)
        resp.raise_for_status()
        return resp.text


async def _render_via_subprocess(props: dict, timeout: int = 30) -> str:
    result = await asyncio.to_thread(
        subprocess.run,
        ["node", str(SSR_BUNDLE), json.dumps(props, ensure_ascii=False)],
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        raise RuntimeError(f"React SSR failed:\n{result.stderr}")

    return result.stdout
