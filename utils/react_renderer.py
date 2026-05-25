import json
import subprocess
from pathlib import Path

from utils.renderer import carregar_estilos_relatorio


ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
REPORT_RENDER_SCRIPT = FRONTEND_DIR / "scripts" / "render-report-html.mjs"


def render_relatorio_html_react(*, dados, graficos, docs_html, cover) -> str:
    payload = {
        "dados": dados,
        "graficos": graficos,
        "docsHtml": docs_html,
        "cover": cover,
        "reportCss": carregar_estilos_relatorio(),
    }

    result = subprocess.run(
        ["node", str(REPORT_RENDER_SCRIPT)],
        cwd=str(FRONTEND_DIR),
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
    )

    return result.stdout
