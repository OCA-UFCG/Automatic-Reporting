from __future__ import annotations

import asyncio
import json
import os
import subprocess
from pathlib import Path

import httpx

BASE_DIR = Path(__file__).resolve().parent.parent
SSR_BUNDLE = BASE_DIR / "report" / "ssr-dist" / "entry.js"
SSR_SERVER_BUNDLE = BASE_DIR / "report" / "ssr-dist" / "server.js"
SSR_PORT = int(os.environ.get("SSR_PORT", "3001"))

_server_process: subprocess.Popen | None = None


def _bundle_path() -> Path:
    """Return the server bundle path if available, else the one-shot entry."""
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


async def render_react_ssr(props: dict, timeout: int = 30) -> str:
    bundle = _bundle_path()

    if not bundle.exists():
        raise RuntimeError(
            f"SSR bundle not found at {bundle}. "
            "Run 'npm run build -w report' first."
        )

    if bundle == SSR_SERVER_BUNDLE:
        return await _render_via_http(props, timeout)
    else:
        return await _render_via_subprocess(props, timeout)


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
