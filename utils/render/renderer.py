import html as html_module
import re

from utils.external.contentful import obter_url_mapa_contentful
from utils.maps import gerar_mapa_regiao, render_mapa_geografico
from utils.render.links import converter_links_para_html
from utils.render.placeholders import substituir_placeholders
from utils.render.sections import identificar_secao_macrotema

_figura_contador = 0


def reset_figura_contador() -> None:
    global _figura_contador
    _figura_contador = 0


__all__ = [
    "converter_links_para_html",
    "render_descricao_tema_html",
    "render_mapa_marker",
    "substituir_placeholders",
    "texto_para_html",
]


FALLBACK_DOC_TEXT = """deu erro.
"""


def render_mapa_marker(contexto: dict, safe_report: str | None = None) -> str:
    contentful_url = obter_url_mapa_contentful(contexto.get("nm_mun", ""))
    if contentful_url:
        cidade_segura = html_module.escape(str(contexto.get("nm_mun", "município")))
        return (
            '<figure class="map-block map-block--region">'
            f'<img class="region-map-image" src="{html_module.escape(contentful_url)}" '
            f'alt="Mapa da região de {cidade_segura}">'
            '</figure>'
            '<!-- fonte: contentful -->'
        )

    mapa_file = gerar_mapa_regiao(contexto.get("nm_mun", ""), safe_report or "relatorio")
    if mapa_file:
        cidade_segura = html_module.escape(str(contexto.get("nm_mun", "município")))
        return (
            '<figure class="map-block map-block--region">'
            f'<img class="region-map-image" src="/output/{html_module.escape(mapa_file)}" '
            f'alt="Mapa da região de {cidade_segura}">'
            '</figure>'
            '<!-- fonte: gerado_localmente -->'
        )

    return render_mapa_geografico(contexto) + '\n<!-- fonte: svg_locator -->'


def render_descricao_tema_html(
    descricao_tema: str,
    contexto: dict,
    namespace: str = "demografia",
    safe_report: str | None = None,
    graficos_por_placeholder: dict[str, str] | None = None,
) -> list[str]:
    partes = []
    for paragrafo in re.split(r"\n\s*\n", descricao_tema):
        paragrafo = paragrafo.strip()
        if not paragrafo:
            continue

        html = texto_para_html(
            paragrafo,
            contexto,
            namespace=namespace,
            graficos_por_placeholder=graficos_por_placeholder,
            safe_report=safe_report,
            classe_paragrafo="theme-detail-text",
        )
        if html:
            partes.append(html)

    return partes


def texto_para_html(
    texto: str,
    contexto: dict,
    namespace: str = "demografia",
    graficos_por_placeholder: dict[str, str] | None = None,
    componentes_html: dict[str, str] | None = None,
    safe_report: str | None = None,
    classe_paragrafo: str = "",
) -> str:

    graficos_por_placeholder = graficos_por_placeholder or {}
    componentes_html = componentes_html or {}

    texto_renderizado = substituir_placeholders(texto, contexto, namespace)

    linhas = [linha.rstrip() for linha in texto_renderizado.splitlines()]

    html_lines = []

    em_lista = False
    em_metadado_docs = False
    metadado_visivel: list[str] | None = None

    proximo_paragrafo_destaque = False

    for linha in linhas:

        linha_limpa = linha.lstrip("\ufeff").strip()

        if metadado_visivel is not None:
            terminou = "@@" in linha_limpa
            conteudo = linha_limpa.split("@@", 1)[0].strip()
            if conteudo:
                metadado_visivel.append(conteudo)
            if terminou:
                texto_metadado = " ".join(metadado_visivel).strip().strip('"“”')
                if texto_metadado:
                    html_lines.append(f"<p>{converter_links_para_html(texto_metadado)}</p>")
                metadado_visivel = None
            continue

        if em_metadado_docs:
            if "@@" in linha_limpa:
                em_metadado_docs = False
            continue

        metadado_match = re.match(r"^([A-Za-z_][\w]*)\s*=", linha_limpa)
        if metadado_match:
            marcador_metadado = metadado_match.group(1).lower()
            if marcador_metadado in {"referencia", "hyperlink"}:
                valor = linha_limpa.split("=", 1)[1].strip()
                terminou = "@@" in valor
                valor = valor.split("@@", 1)[0].strip()
                metadado_visivel = [valor] if valor else []
                if terminou:
                    texto_metadado = " ".join(metadado_visivel).strip().strip('"“”')
                    if texto_metadado:
                        html_lines.append(f"<p>{converter_links_para_html(texto_metadado)}</p>")
                    metadado_visivel = None
                continue
            if "@@" not in linha_limpa and marcador_metadado != "descricao_tema":
                em_metadado_docs = True
            continue

        # LINHA VAZIA
        if not linha_limpa:
            if em_lista:
                html_lines.append("</ul>")
                em_lista = False

            continue

        # GRÁFICOS
        marcador_grafico = re.fullmatch(
            r"%%(\w+(?:\+\w+)*)",
            linha_limpa,
        )

        if marcador_grafico:

            if em_lista:
                html_lines.append("</ul>")
                em_lista = False

            tipos = [
                tipo.strip()
                for tipo in marcador_grafico.group(1).split("+")
            ]

            figuras = []

            for tipo in tipos:

                chart_file = graficos_por_placeholder.get(tipo)

                if not chart_file:
                    continue

                figuras.append(
                    '<figure style="text-align:center; margin:0; flex:1; min-width:280px;">'
                    f'<img src="/output/{html_module.escape(chart_file)}" '
                    f'alt="{html_module.escape(tipo)}" '
                    'style="width:100%; max-width:480px; object-fit:contain;">'
                    "</figure>"
                )

            if figuras:

                html_lines.append(
                    '<div style="display:flex; gap:24px; justify-content:center; '
                    'align-items:flex-start; margin:32px 0; flex-wrap:wrap;">'
                    + "".join(figuras)
                    + "</div>"
                )

            continue

        # TÍTULO PRINCIPAL
        if linha_limpa.startswith("#!"):

            if em_lista:
                html_lines.append("</ul>")
                em_lista = False

            titulo = linha_limpa[2:].strip()

            if titulo:
                html_lines.append(
                    f"<h1>{html_module.escape(titulo)}</h1>"
                )

            continue

        # LISTAS
        if linha_limpa.startswith(("- ", "• ", "* ")):

            if not em_lista:
                html_lines.append("<ul>")
                em_lista = True

            item = converter_links_para_html(linha_limpa[2:].strip())

            html_lines.append(f"<li>{item}</li>")

            continue

        if em_lista:
            html_lines.append("</ul>")
            em_lista = False

        # SEÇÕES
        secao_macrotema = identificar_secao_macrotema(
            linha_limpa,
            namespace,
        )

        if secao_macrotema:
            proximo_paragrafo_destaque = False
            continue

        elif (
            re.match(r"^\d+\.\s+", linha_limpa)
            or linha_limpa.lower()
            in {"apresentação", "demografia"}
        ):

            html_lines.append(
                f"<h2>{html_module.escape(linha_limpa)}</h2>"
            )

            proximo_paragrafo_destaque = False

        elif re.match(
            r"^figura\s+(?:[&a-z]|\d+)\s*[–-]",
            linha_limpa,
            flags=re.IGNORECASE,
        ):

            global _figura_contador
            _figura_contador += 1

            legenda = re.sub(
                r"\[[A-Za-z0-9]{1,3}\]",
                "",
                linha_limpa,
            ).replace("&", "")

            legenda = re.sub(
                r"^figura\s+[^–-]*[–-]",
                f"Figura {_figura_contador} –",
                legenda,
                flags=re.IGNORECASE,
            )

            html_lines.append(
                f'<p class="figure-caption">'
                f"{html_module.escape(legenda.strip())}"
                f"</p>"
            )

            proximo_paragrafo_destaque = False

        else:

            linha_limpa = re.sub(
                r"\[[A-Za-z0-9]{1,3}\]",
                "",
                linha_limpa,
            )

            if classe_paragrafo:
                classe = f' class="{classe_paragrafo}"'
            elif proximo_paragrafo_destaque:
                classe = ' class="lead"'
            else:
                classe = ""

            html_lines.append(
                f"<p{classe}>"
                f"{converter_links_para_html(linha_limpa)}"
                f"</p>"
            )

            proximo_paragrafo_destaque = False

    if em_lista:
        html_lines.append("</ul>")

    return "\n".join(html_lines)