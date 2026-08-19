import html as html_module
import re

from utils.data.macrotemas import MACROTEMA_SECOES


def normalizar_titulo_para_match(texto: str) -> str:
    texto = re.sub(r"^\s*\d+\s*\.?\s*", "", texto).strip()
    texto = re.sub(r"\s+", " ", texto)
    return texto.casefold()


def identificar_secao_macrotema(linha: str, namespace: str) -> dict[str, object] | None:
    secao = MACROTEMA_SECOES.get(namespace)
    if not secao:
        return None

    titulo_normalizado = normalizar_titulo_para_match(linha)
    aliases = [alias.casefold() for alias in secao["aliases"]]
    if titulo_normalizado in aliases or secao["titulo"].casefold() == titulo_normalizado:
        return secao
    return None


def render_section_heading(secao: dict[str, object]) -> str:
    numero = html_module.escape(str(secao["numero"]))
    titulo = html_module.escape(str(secao["titulo"]))
    return (
        '<div class="section-heading">'
        f'<span class="section-number">{numero}</span>'
        f'<div class="section-title-wrap"><span class="section-title">{titulo}</span></div>'
        '</div>'
    )
