from __future__ import annotations

import json
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SSR_BUNDLE = BASE_DIR / "report" / "ssr-dist" / "ssr-entry.js"


def render_react_ssr(props: dict, timeout: int = 30) -> str:
    if not SSR_BUNDLE.exists():
        raise RuntimeError(
            f"SSR bundle not found at {SSR_BUNDLE}. "
            "Run 'npm run build' in the report/ directory first."
        )

    result = subprocess.run(
        ["node", str(SSR_BUNDLE), json.dumps(props, ensure_ascii=False)],
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        raise RuntimeError(f"React SSR failed:\n{result.stderr}")

    return result.stdout
