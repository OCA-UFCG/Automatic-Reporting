import re
import html as html_module  #renomeado para evitar conflito com a variável local 'html_content'
from jinja2 import Environment

from utils.macrotemas import MACROTEMA_SECOES
from utils.tables import render_tabela_resumo


FALLBACK_DOC_TEXT = """deu erro.
"""

TEMPLATE_STRING = """
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Data Nordeste – Relatório modelo</title>
    <style>
        body {
            font-family: Georgia, "Times New Roman", serif;
            max-width: 920px;
            margin:0 auto 2px;
            padding: 0 24px;
            line-height: 1.48;
            font-size: 16px;
            color: #222;
        }
        h1 {
            font-size: 30px;
            font-weight: 700;
            margin: 0 0 14px 0;
        }
        h2 {
            font-size: 24px;
            font-weight: 700;
            margin: 30px 0 10px 0;
        }
        p {
            margin: 0 0 14px 0;
            text-align: justify;
        }
        .field {
            font-size: 17px;
            margin-bottom: 8px;
        }
        .field strong {
            font-weight: 700;
        }
        .indent {
            text-indent: 1.5em;
        }
        ul {
            margin: 8px 0 16px 28px;
        }
        li {
            margin-bottom: 6px;
        }
        .doc-content p {
            font-family: Arial, sans-serif;
            text-indent: 0;
        }
        .doc-content p.lead {
            font-family: Georgia, "Times New Roman", serif;
            font-size: 18px;
            font-style: italic;
            line-height: 1.38;
            color: #3d3d3d;
            margin: 10px 0 24px;
        }
        .doc-content h1 {
            font-size: 34px;
            font-weight: 700;
            margin: 0 0 18px 0;
        }
        .doc-content ul {
            text-indent: 0;
        }
        .section-heading {
            display: grid;
            grid-template-columns: auto 1fr;
            align-items: end;
            column-gap: 16px;
            margin: 14px 0 10px;
        }
        .section-number {
            color: #c68a2c;
            font-size: 56px;
            line-height: 0.9;
            font-weight: 400;
        }
        .section-title-wrap {
            padding-bottom: 7px;
            border-bottom: 1px solid #d99a37;
        }
        .section-title {
            color: #255235;
            font-size: 29px;
            line-height: 1;
            font-weight: 400;
        }
        .chart-block {
            margin: 18px auto 20px;
            text-align: center;
            break-inside: avoid;
        }
        .chart-block img {
            display: block;
            max-width: 78%;
            height: auto;
            margin: 0 auto;
        }
        .figure-caption {
            margin: 8px auto 16px;
            max-width: 76%;
            color: #333;
            font-family: Arial, sans-serif;
            font-size: 13px;
            line-height: 1.35;
            text-align: center;
        }
        .map-block {
            width: 100%;
            max-width: 420px;
            margin: 16px auto 22px;
            break-inside: avoid;
            text-align: center;
            overflow: hidden;
            border: 1px solid #b9b9b9;
            background: #f7f7f7;
            padding: 6px 6px 4px;
        }
        .map-title {
            color: #111;
            font-family: Arial, sans-serif;
            font-size: 12px;
            line-height: 1.2;
            margin: 0 0 4px;
            text-align: center;
        }
        .map-frame {
            width: 100%;
            aspect-ratio: 220 / 194;
            height: auto;
            border: 1px solid #c8d6dd;
            box-sizing: border-box;
            overflow: hidden;
            background: #bfe3f1;
            position: relative;
        }
        .locator-map {
            display: block;
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        .map-block figcaption {
            margin-top: 4px;
            color: #111;
            font-family: Arial, sans-serif;
            font-size: 12px;
            line-height: 1.2;
        }
        .locator-label {
            position: absolute;
            transform: translate(-100%, -50%);
            margin-left: -8px;
            color: #111;
            font: 700 12px Arial, sans-serif;
            text-shadow: 0 1px 2px #fff, 0 -1px 2px #fff, 1px 0 2px #fff, -1px 0 2px #fff;
            white-space: nowrap;
            pointer-events: none;
        }
        .state-label {
            position: absolute;
            transform: translate(-50%, -50%);
            color: #111;
            font: 700 9px Arial, sans-serif;
            line-height: 1;
            text-shadow: 0 1px 2px #fff, 0 -1px 2px #fff, 1px 0 2px #fff, -1px 0 2px #fff;
            pointer-events: none;
        }
        .locator-dot {
            position: absolute;
            width: 9px;
            height: 9px;
            transform: translate(-50%, -50%);
            border: 1.5px solid #8f1d14;
            border-radius: 999px;
            background: #d7191c;
            box-sizing: border-box;
            box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.75);
            pointer-events: none;
        }
        .region-legend {
            display: grid;
            grid-template-columns: repeat(2, max-content);
            gap: 4px 12px;
            justify-content: center;
            margin: 7px 0 3px;
            font-family: Arial, sans-serif;
            font-size: 11px;
            color: #111;
        }
        .region-legend-item {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            white-space: nowrap;
        }
        .region-legend-swatch {
            width: 10px;
            height: 10px;
            border: 1px solid rgba(0, 0, 0, 0.35);
            border-radius: 2px;
        }
        .map-fallback {
            display: grid;
            gap: 6px;
            place-items: center;
            min-height: 220px;
            border: 1px solid #d8d0bf;
            background: #f5f0e8;
            color: #255235;
            font-family: Arial, sans-serif;
        }
        .map-fallback a {
            color: #bd6039;
            font-size: 13px;
            font-weight: 700;
        }
        .report-cover {
            margin: 0 0 34px;
            font-family: Arial, sans-serif;
            color: #25262a;
            break-inside: avoid;
        }
       .cover-header {
    width: 100vw;
    height: 10%;
    margin-left: calc(50% - 50vw);
    margin-right: calc(50% - 50vw);
    margin-bottom: 24px;
    padding: 12px 24px;
    background: #eeeeef;
    box-sizing: border-box;
}
        .cover-meta {
            position: relative;
            display: flex;
            justify-content:right;
            align-items: right;
            margin-bottom: 0;
            font-size: 14px;
        }
        .cover-brand {
    position: absolute;
    left: 0;
    display: inline-grid;
    gap: 2px;
    line-height: 1;
}
        .brand-mark {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            color: #008d43;
            font-size: 26px;
            font-weight: 900;
            letter-spacing: 0;
        }
        .brand-squares {
            display: grid;
            grid-template-columns: repeat(3, 4px);
            gap: 2px;
        }
        .brand-squares span {
            width: 4px;
            height: 4px;
        }
        .brand-squares span:nth-child(1),
        .brand-squares span:nth-child(5) { background: #ef7d00; }
        .brand-squares span:nth-child(2),
        .brand-squares span:nth-child(6) { background: #0a8f43; }
        .brand-squares span:nth-child(3),
        .brand-squares span:nth-child(4) { background: #204f9e; }
        .brand-subtitle {
            color: #222;
            font-size: 5px;
            font-weight: 700;
            letter-spacing: 0.3px;
            text-transform: uppercase;
        }
        .cover-date {
            color: #2f3033;
            font-size: 14px;
            white-space: nowrap;
            text-align: center;
            transform: translateY(6px);
        }
        .cover-content {
            padding: 0;
        }
        .cover-kicker {
            margin-bottom: 10px;
            color: #005e2f;
            font-size: 16px;
            font-weight: 500;
        }
        .cover-city {
            margin: 0 0 24px;
            color: #2b2c30;
            font-family: Arial, sans-serif;
            font-size: 34px;
            font-weight: 800;
            line-height: 1.05;
            letter-spacing: 0;
        }
        .cover-metrics {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 22px;
            margin-bottom: 26px;
        }
        .metric-card {
            min-height: 88px;
            padding: 13px 12px 10px;
            border: 1px solid #e7e7ea;
            border-radius: 8px;
            background: #fbfbfc;
            box-shadow: 0 8px 18px rgba(23, 28, 38, 0.06);
            box-sizing: border-box;
        }
        .metric-heading {
            display: grid;
            grid-template-columns: 18px 1fr;
            gap: 8px;
            align-items: center;
            margin-bottom: 11px;
        }
        .metric-icon {
            width: 18px;
            height: 18px;
            color: #008d43;
        }
        .metric-label {
            color: #1f2227;
            font-size: 11px;
            font-weight: 700;
            line-height: 1.15;
        }
        .metric-source {
            margin-top: 1px;
            color: #8a8d95;
            font-size: 7px;
            line-height: 1.1;
        }
        .metric-value {
            color: #008d43;
            font-family: Arial, sans-serif;
            font-size: 21px;
            font-weight: 800;
            line-height: 1;
            white-space: nowrap;
        }
        .metric-unit {
            font-size: 15px;
            font-weight: 800;
        }
        .metric-caption {
            margin-top: 8px;
            color: #8a8d95;
            font-size: 7px;
            line-height: 1.1;
        }
        .executive-summary {
            padding-top: 0;
        }
        .executive-title {
            margin: 0 0 8px;
            color: #005e2f;
            font-family: Arial, sans-serif;
            font-size: 17px;
            font-weight: 700;
            text-transform: none;
        }
        .executive-summary p {
            margin: 0;
            color: #555;
            font-family: Arial, sans-serif;
            font-size: 14px;
            line-height: 1.45;
            text-align: left;
        }
        @media (max-width: 760px) {
            .cover-metrics {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
    </style>
</head>
<body>
<section class="report-cover">
    <div class="cover-header">
        <div class="cover-meta">
            <div class="cover-brand" aria-label="Data Nordeste">
                <div class="brand-mark">
                    <span class="brand-squares" aria-hidden="true"><span></span><span></span><span></span><span></span><span></span><span></span></span>
                    <span>NE</span>
                </div>
                <span class="brand-subtitle">Data Nordeste</span>
            </div>
            <span class="cover-date">{{ cover.data_extenso }}</span>
        </div>
    </div>
    <div class="cover-content">
        <div class="cover-kicker">Relatório geral</div>
        <h1 class="cover-city">{{ cover.cidade_nome }}{% if cover.uf %} ({{ cover.uf }}){% endif %}</h1>
        <div class="cover-metrics">
            {% for metrica in cover.metricas %}
            <div class="metric-card">
                <div class="metric-heading">
                    <svg class="metric-icon" viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M4 17h16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                        <path d="M7 15l3.1-4.2 2.7 2.8 3.3-5.1L20 15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                        <circle cx="10.1" cy="10.8" r="1.1" fill="currentColor"/>
                        <circle cx="12.8" cy="13.6" r="1.1" fill="currentColor"/>
                        <circle cx="16.1" cy="8.5" r="1.1" fill="currentColor"/>
                    </svg>
                    <div>
                        <div class="metric-label">{{ metrica.rotulo }}</div>
                        <div class="metric-source">{{ metrica.fonte }}</div>
                    </div>
                </div>
                <div class="metric-value">{{ metrica.valor }}{% if metrica.sufixo %} <span class="metric-unit">{{ metrica.sufixo }}</span>{% endif %}</div>
                <div class="metric-caption">{{ metrica.caption }}</div>
            </div>
            {% endfor %}
        </div>
        <div class="executive-summary">
            <h2 class="executive-title">Radar da região</h2>
            <p>A síntese a seguir classifica os sete temas estratégicos do município segundo os parâmetros de referência adotados pela plataforma Data NE. Cada tema é detalhado nas seções subsequentes.</p>
        </div>
    </div>
</section>
{% for linha in dados %}
<div class="doc-content">{{ docs_html | safe }}</div>
{% endfor %}
</body>
</html>
"""


def render_chart_placeholder(chart_file: str) -> str:
    return (
        '<div class="chart-block">'
        f'<img src="/output/{html_module.escape(chart_file)}" alt="Gráfico">'
        '</div>'
    )


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


def texto_para_html(
    texto: str,
    contexto: dict,
    namespace: str = "demografia",
    graficos_por_placeholder: dict[str, str] | None = None,
    componentes_html: dict[str, str] | None = None,
) -> str:

    def substituir_placeholder_dolar(match: re.Match) -> str:
        placeholder_namespace = match.group(1).lower()
        campo = match.group(2)

        namespaces_validos = {
            namespace.lower(),
            "linha",
            "dados",
            "csv",
        }

        if placeholder_namespace in namespaces_validos:
            return str(contexto.get(campo, match.group(0)))

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

    LEGENDAS_GRAFICOS = {
        "grafico_sexo": "População por sexo",
        "grafico_porte": "Distribuição por porte",
        "grafico_top_cidades": "Top cidades",
    }

    graficos_por_placeholder = graficos_por_placeholder or {}
    componentes_html = componentes_html or {}

    texto_normalizado = texto

    texto_normalizado = re.sub(
        r"\$([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)",
        substituir_placeholder_dolar,
        texto_normalizado,
    )

    for alias, valor in alias_map.items():
        texto_normalizado = texto_normalizado.replace(
            f"${alias}",
            str(valor),
        )

    texto_renderizado = Environment().from_string(
        texto_normalizado
    ).render(**contexto)

    linhas = [linha.rstrip() for linha in texto_renderizado.splitlines()]

    html_lines = []

    em_lista = False

    proximo_paragrafo_destaque = namespace in MACROTEMA_SECOES

    figura_contador = 0

    for linha in linhas:

        linha_limpa = linha.lstrip("\ufeff").strip()

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

            mapa_html = componentes_html.get("mapa_geografico")

            if mapa_html:
                html_lines.append(mapa_html)

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

            html_lines.append(
                render_section_heading(secao_macrotema)
            )

            proximo_paragrafo_destaque = True

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
                f"{html_module.escape(linha_limpa)}"
                f"</p>"
            )

            proximo_paragrafo_destaque = False

    if em_lista:
        html_lines.append("</ul>")

    return "\n".join(html_lines)
