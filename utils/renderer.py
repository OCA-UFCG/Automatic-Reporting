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
            margin: 32px auto;
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
        .report-cover {
            margin: 56px 0 34px;
            font-family: Arial, sans-serif;
            color: #555;
        }
        .cover-stripe {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            height: 5px;
            margin-bottom: 12px;
        }
        .cover-stripe span:nth-child(1) { background: #225236; }
        .cover-stripe span:nth-child(2) { background: #bd6039; }
        .cover-stripe span:nth-child(3) { background: #d79a3b; }
        .cover-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 28px;
            font-size: 14px;
        }
        .cover-brand,
        .cover-kicker,
        .executive-title {
            color: #bd6039;
            font-weight: 700;
            text-transform: uppercase;
        }
        .cover-kicker {
            margin-bottom: 8px;
            font-size: 15px;
        }
        .cover-city {
            margin: 0;
            color: #255235;
            font-family: Georgia, "Times New Roman", serif;
            font-size: 60px;
            font-weight: 400;
            line-height: 0.95;
            letter-spacing: -1px;
        }
        .cover-city-separator {
            color: #d19a3a;
        }
        .cover-subtitle {
            margin: 6px 0 32px;
            color: #5e5e5e;
            font-family: Georgia, "Times New Roman", serif;
            font-size: 18px;
            font-style: italic;
            line-height: 1.35;
            text-align: left;
        }
        .cover-metrics {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 22px;
            margin-bottom: 20px;
        }
        .metric-card {
            border-left: 3px solid #d19a3a;
            padding-left: 12px;
        }
        .metric-label {
            margin-bottom: 6px;
            color: #666;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
        }
        .metric-value {
            color: #255235;
            font-family: Georgia, "Times New Roman", serif;
            font-size: 32px;
            line-height: 1;
        }
        .metric-caption {
            margin-top: 6px;
            font-size: 12px;
        }
        .executive-summary {
            border-top: 1px solid #dfd6c5;
            padding-top: 20px;
        }
        .executive-title {
            margin: 0 0 6px;
            font-family: Arial, sans-serif;
            font-size: 21px;
        }
        .executive-summary p {
            margin: 0;
            color: #555;
            font-family: Arial, sans-serif;
            font-size: 14px;
            line-height: 1.45;
            text-align: left;
        }
    </style>
</head>
<body>
<section class="report-cover">
    <div class="cover-stripe"><span></span><span></span><span></span></div>
    <div class="cover-meta">
        <span class="cover-brand">Plataforma Data NE</span>
        <span>{{ cover.data_extenso }}</span>
    </div>
    <div class="cover-kicker">Relatório Municipal</div>
    <h1 class="cover-city">{{ cover.cidade_nome }}<span class="cover-city-separator">·</span>{{ cover.uf }}</h1>
    <p class="cover-subtitle">{{ cover.descricao }}</p>
    <div class="cover-metrics">
        <div class="metric-card">
            <div class="metric-label">População</div>
            <div class="metric-value">{{ cover.populacao }}</div>
            <div class="metric-caption">habitantes · Censo 2022</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">PIB</div>
            <div class="metric-value">R$ 6,48 bi</div>
            <div class="metric-caption">per capita R$ 29.711</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Alfabetização</div>
            <div class="metric-value">86,90%</div>
            <div class="metric-caption">população 15+ anos</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Vacinação</div>
            <div class="metric-value">76,55%</div>
            <div class="metric-caption">cobertura em 2024</div>
        </div>
    </div>
    <div class="executive-summary">
        <h2 class="executive-title">Resumo Executivo Por Tema</h2>
        <p>A síntese a seguir classifica os sete temas estratégicos do município segundo os parâmetros de referência adotados pela plataforma Data NE. Cada tema é detalhado nas seções subsequentes.</p>
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
            r"^figura\s+[&x]\s*[–-]",
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