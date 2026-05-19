from pathlib import Path
from jinja2 import Environment, FileSystemLoader


FALLBACK_DOC_TEXT = """deu erro.
"""

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
CSS_PATH = TEMPLATE_DIR / "report.css"


def criar_template_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def carregar_estilos_relatorio() -> str:
    return CSS_PATH.read_text(encoding="utf-8")


def render_relatorio_html(*, dados, graficos, docs_html, cover) -> str:
    template = criar_template_environment().get_template("report.html")
    return template.render(
        dados=dados,
        graficos=graficos,
        docs_html=docs_html,
        cover=cover,
        report_css=carregar_estilos_relatorio(),
    )
