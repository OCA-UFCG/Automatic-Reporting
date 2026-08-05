import html as html_module
import re

from utils.contentful import obter_url_mapa_contentful
from utils.macrotemas import MACROTEMA_SECOES
from utils.maps import gerar_mapa_regiao, render_mapa_geografico
from utils.tables import render_tabela_resumo


def converter_links_para_html(texto: str) -> str:
    resultado = []
    ultimo_fim = 0
    for m in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', texto):
        resultado.append(html_module.escape(texto[ultimo_fim:m.start()]))
        resultado.append(
            f'<a href="{html_module.escape(m.group(2))}">'
            f'{html_module.escape(m.group(1))}'
            f'</a>'
        )
        ultimo_fim = m.end()
    resultado.append(html_module.escape(texto[ultimo_fim:]))
    return "".join(resultado)


FALLBACK_DOC_TEXT = """deu erro.
"""

def render_chart_placeholder(chart_file: str) -> str:
    return (
        '<div class="chart-block">'
        f'<img src="/output/{html_module.escape(chart_file)}" alt="Gráfico">'
        '</div>'
    )


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


def render_descricao_tema_html(descricao_tema: str, contexto: dict, namespace: str = "demografia", safe_report: str | None = None) -> list[str]:
    partes = []
    map_count = 0
    for paragrafo in re.split(r"\n\s*\n", descricao_tema):
        paragrafo = paragrafo.strip()
        if not paragrafo:
            continue

        if paragrafo.lstrip("\ufeff").strip().lower() in {"*mapa_geografico", "mapa_geografico"}:
            if map_count < 2:
                partes.append(render_mapa_marker(contexto, safe_report))
                map_count += 1
        else:
            paragrafo = substituir_placeholders(paragrafo, contexto, namespace)
            partes.append(
                f'<p class="theme-detail-text">{converter_links_para_html(paragrafo)}</p>'
            )

    return partes


def _resolver_caminho_em_contexto(contexto: dict, caminho: str) -> object | None:
    atual: object = contexto
    for parte in caminho.split("."):
        if not isinstance(atual, dict) or parte not in atual:
            return None
        atual = atual[parte]
    return atual


def _resolver_campo_com_alias(contexto: dict, campo: str) -> object | None:
    valor = _resolver_caminho_em_contexto(contexto, campo)
    if valor is not None:
        return valor

    if campo == "city":
        return _resolver_caminho_em_contexto(contexto, "nm_mun")

    if campo == "municipio":
        return _resolver_caminho_em_contexto(contexto, "nm_mun")

    if campo == "year":
        return _resolver_caminho_em_contexto(contexto, "ano")

    if campo == "ano":
        return _resolver_caminho_em_contexto(contexto, "year")

    return None


def _resolver_contexto_por_alias(contexto: dict, alias: str, namespace: str) -> dict:
    if alias == namespace.lower():
        return contexto

    valor_alias = contexto.get(alias)
    if isinstance(valor_alias, dict):
        return valor_alias

    return contexto


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


def substituir_placeholders(texto: str, contexto: dict, namespace: str = "demografia") -> str:
    alias_de_tabela = {
        "table": _resolver_contexto_por_alias(contexto, "table", namespace),
        "tabela": _resolver_contexto_por_alias(contexto, "tabela", namespace),
        "sheet": _resolver_contexto_por_alias(contexto, "sheet", namespace),
        "planilha": _resolver_contexto_por_alias(contexto, "planilha", namespace),
        "linha": contexto,
        "dados": contexto,
        "csv": contexto,
    }

    def _substituir_dolar(match: re.Match) -> str:
        placeholder_namespace = match.group(1).lower()
        campo = match.group(2)

        namespaces_validos = {
            namespace.lower(),
        }

        namespaces_validos.update(alias_de_tabela.keys())

        if placeholder_namespace in namespaces_validos:
            contexto_alvo = alias_de_tabela[placeholder_namespace]
            if isinstance(contexto_alvo, dict):
                valor = _resolver_campo_com_alias(contexto_alvo, campo)
                if valor is not None:
                    return str(valor)
            return match.group(0)

        return match.group(0)

    alias_map = {
        "city": contexto.get("nm_mun", ""),
        "year": contexto.get("ano", ""),
        "municipio": contexto.get("nm_mun", ""),
        "ano": contexto.get("ano", ""),
        "data_relatorio": contexto.get("data_relatorio", ""),
        "hora_relatorio": contexto.get("hora_relatorio", ""),
        "data_geracao": contexto.get("data_relatorio", ""),
        "hora_geracao": contexto.get("hora_relatorio", ""),
    }

    resultado = texto

    resultado = re.sub(
        r"\$([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)",
        _substituir_dolar,
        resultado,
    )

    for alias, valor in alias_map.items():
        resultado = resultado.replace(f"${alias}", str(valor))

    resultado = re.sub(
        r'\{\{\s*(\w+)\s*\}\}',
        lambda m: str(contexto.get(m.group(1), m.group(0))),
        resultado,
    )

    return resultado


def texto_para_html(
    texto: str,
    contexto: dict,
    namespace: str = "demografia",
    graficos_por_placeholder: dict[str, str] | None = None,
    componentes_html: dict[str, str] | None = None,
    safe_report: str | None = None,
) -> str:

    LEGENDAS_GRAFICOS = {
        "grafico_sexo": "População por sexo",
        "grafico_porte": "Distribuição por porte",
        "grafico_top_cidades": "Top cidades",
    }

    graficos_por_placeholder = graficos_por_placeholder or {}
    componentes_html = componentes_html or {}

    texto_renderizado = substituir_placeholders(texto, contexto, namespace)

    linhas = [linha.rstrip() for linha in texto_renderizado.splitlines()]

    html_lines = []

    em_lista = False
    em_metadado_docs = False

    proximo_paragrafo_destaque = False

    figura_contador = 0

    for linha in linhas:

        linha_limpa = linha.lstrip("\ufeff").strip()

        if em_metadado_docs:
            if "@@" in linha_limpa:
                em_metadado_docs = False
            continue

        metadado_match = re.match(r"^([A-Za-z_][\w]*)\s*=", linha_limpa)
        if metadado_match:
            marcador_metadado = metadado_match.group(1).lower()
            if "@@" not in linha_limpa and marcador_metadado != "descricao_tema":
                em_metadado_docs = True
            continue

        # LINHA VAZIA
        if not linha_limpa:
            if em_lista:
                html_lines.append("</ul>")
                em_lista = False

            continue

        # MAPA GEOGRÁFICO
        if linha_limpa.lower() in {"*mapa_geografico", "mapa_geografico"}:

            if em_lista:
                html_lines.append("</ul>")
                em_lista = False

            html_lines.append(render_mapa_marker(contexto, safe_report))
            continue

        # COMPONENTES
        marcador_componente = re.fullmatch(
            r"##([A-Za-z_][\w]*)",
            linha_limpa,
        )

        if marcador_componente:

            if em_lista:
                html_lines.append("</ul>")
                em_lista = False

            nome_componente = marcador_componente.group(1)

            if nome_componente == "tabela_resumo":

                html_lines.append(
                    render_tabela_resumo(
                        contexto=contexto,
                        namespace=namespace,
                    )
                )

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

                figura_contador += 1

                legenda = " e ".join(
                    LEGENDAS_GRAFICOS.get(tipo, tipo)
                    for tipo in tipos
                )

                html_lines.append(
                    '<div style="display:flex; gap:24px; justify-content:center; '
                    'align-items:flex-start; margin:32px 0; flex-wrap:wrap;">'
                    + "".join(figuras)
                    + "</div>"
                )

                html_lines.append(
                    f'<p class="figure-caption">'
                    f'Figura {figura_contador} - '
                    f'{html_module.escape(legenda)}'
                    f"</p>"
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

            item = html_module.escape(
                linha_limpa[2:].strip()
            )

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
            r"^figura\s+(?:[&x]|\d+)\s*[–-]",
            linha_limpa,
            flags=re.IGNORECASE,
        ):

            legenda = re.sub(
                r"\[[A-Za-z0-9]{1,3}\]",
                "",
                linha_limpa,
            ).replace("&", "")

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

            classe = (
                ' class="lead"'
                if proximo_paragrafo_destaque
                else ""
            )

            html_lines.append(
                f"<p{classe}>"
                f"{converter_links_para_html(linha_limpa)}"
                f"</p>"
            )

            proximo_paragrafo_destaque = False

    if em_lista:
        html_lines.append("</ul>")

    return "\n".join(html_lines)
