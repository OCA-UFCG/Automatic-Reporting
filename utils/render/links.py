import html as html_module
import re


def converter_links_para_html(texto: str) -> str:
    resultado = []
    ultimo_fim = 0
    padrao_link = re.compile(r'\[([^\]]+)\]\(([^)]+)\)|(https?://[^\s<>“”"]+)')
    for m in padrao_link.finditer(texto):
        resultado.append(html_module.escape(texto[ultimo_fim:m.start()]))
        url = m.group(2) or m.group(3)
        rotulo = m.group(1) or url
        resultado.append(
            f'<a href="{html_module.escape(url)}">'
            f'{html_module.escape(rotulo)}'
            f'</a>'
        )
        ultimo_fim = m.end()
    resultado.append(html_module.escape(texto[ultimo_fim:]))
    return "".join(resultado)
