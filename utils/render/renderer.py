import base64
import html as html_module
import re
from urllib.parse import quote

from config import BASE_DIR
from utils.maps import (
    buscar_mapa_estatico,
    gerar_mapa_regiao,
    render_mapa_geografico,
)
from utils.render.links import _url_is_safe, convert_links_to_html
from utils.render.placeholders import (
    interpretar_blocos_condicionais,
    substituir_placeholders,
)
from utils.render.sections import identificar_secao_macrotema

_figura_contador = 1
_proxima_referencia_inline = 1
# Um marcador de gráfico que não gerou imagem (ex.: município sem comércio
# exterior) deixava a legenda seguinte órfã no relatório, e ainda consumindo
# um número de figura. O marcador sinaliza aqui que a próxima legenda deve ser
# descartada. É estado de módulo, e não local, porque
# render_descricao_tema_html quebra o texto em parágrafos e chama
# texto_para_html uma vez para cada um: marcador e legenda caem em chamadas
# diferentes sempre que há linha em branco entre eles no Doc.
_suprimir_proxima_legenda = False

_LARGURA_MAXIMA_GRAFICO_PADRAO = "480px"
_MARGEM_VERTICAL_GRAFICOS_PADRAO = "32px"
_CONFIG_GRAFICOS = {
    "grafico_composicao_cor_raca": {
        "largura_maxima": "350px",
        "margem_vertical": "12px",
    },
    "grafico_tecnologias_acesso_agua": {
        "largura_maxima": "560px",
        "margem_vertical": "16px",
    },
}


def reset_figura_contador() -> None:
    global _figura_contador, _proxima_referencia_inline
    global _suprimir_proxima_legenda
    _figura_contador = 1
    _proxima_referencia_inline = 1
    _suprimir_proxima_legenda = False


_REFERENCIA_FIGURA_INLINE = re.compile(r"(?i)\bfigura\s+\[?[Xx&]\]?\b")


def _substituir_referencia_figura_inline(linha: str) -> str:
    """Substitui menções inline como "(Figura X)" pelo número real da figura.

    O texto fonte referencia, no meio de um parágrafo, a figura que é
    legendada logo em seguida usando um placeholder (``X``, ``&``, opcionalmente
    entre colchetes) em vez do número final — que só é conhecido em tempo de
    renderização. O regex é ancorado nesses placeholders (não em qualquer
    palavra curta após "figura") para não casar frases comuns como "a figura
    da variação" ou menções que já trazem o número final, como "Figura 2".

    Quando um parágrafo menciona mais de uma figura (ex.: "(Figura X)... e
    (Figura X)..."), cada ocorrência é contada separadamente e aponta para a
    figura seguinte na sequência, na ordem em que aparecem.
    """
    def _proxima_figura(_match: re.Match) -> str:
        global _proxima_referencia_inline
        _proxima_referencia_inline += 1
        return f"Figura {_proxima_referencia_inline}"

    return _REFERENCIA_FIGURA_INLINE.sub(_proxima_figura, linha)


__all__ = [
    "convert_links_to_html",
    "render_descricao_tema_html",
    "render_mapa_marker",
    "reset_figura_contador",
    "substituir_placeholders",
    "texto_para_html",
]


FALLBACK_DOC_TEXT = """deu erro.
"""


def render_mapa_marker(contexto: dict, safe_report: str | None = None) -> str:
    mapa_estatico = buscar_mapa_estatico(
        contexto.get("nm_mun", ""), contexto.get("sigla_uf")
    )
    if mapa_estatico:
        cidade_segura = html_module.escape(str(contexto.get("nm_mun", "município")))
        return (
            '<figure class="map-block map-block--region">'
            f'<img class="region-map-image" src="/mapas/{quote(mapa_estatico)}" '
            f'alt="Mapa da região de {cidade_segura}">'
            '<figcaption>Figura 1- Localização do município.</figcaption>'
            '</figure>'
            '<!-- fonte: mapa_estatico -->'
        )

    mapa_file = gerar_mapa_regiao(contexto.get("nm_mun", ""), safe_report or "relatorio")
    if mapa_file:
        cidade_segura = html_module.escape(str(contexto.get("nm_mun", "município")))
        return (
            '<figure class="map-block map-block--region">'
            f'<img class="region-map-image" src="/output/{html_module.escape(mapa_file)}" '
            f'alt="Mapa da região de {cidade_segura}">'
            '<figcaption>Figura 1- Localização do município.</figcaption>'
            '</figure>'
            '<!-- fonte: gerado_localmente -->'
        )

    return render_mapa_geografico(contexto) + '\n<!-- fonte: svg_locator -->'


_SECOES_TITULO_ESPECIAL = {
    "síntese", "sintese",
    "conteúdos relacionados", "conteudos relacionados",
    "fontes", "referências", "referencias",
}
_SECOES_CAIXA_FONTES = {"fontes", "conteúdos relacionados", "conteudos relacionados"}

# Ex.: "[Painel: Terceira Idade](https://...)" ou "[Narrativa de dados: X](https://...)".
_BADGE_LINK = re.compile(
    r"(?i)^\[\s*(painel|narrativa de dados)\s*:\s*([^\]]*?)\s*\]\((\S+)\)$"
)

# Ex.: "demografia.“$nm_datastory1” = https://...". Roda depois de
# substituir_placeholders, então "$campo" só sobra aqui se não tinha valor.
_LINHA_NARRATIVA_DADOS = re.compile(
    r"(?i)^[a-z][\w-]*\.\s*(.+?)\s*=\s*(https?://\S+)$"
)


_LINK_DATA_NORDESTE = "https://qr.codes/Bw7u3I"
_QR_DATA_NORDESTE_PATH = BASE_DIR / "report" / "src" / "assets" / "qr-code-datanordeste.png"


def _carregar_qr_data_nordeste() -> str:
    try:
        dados = _QR_DATA_NORDESTE_PATH.read_bytes()
    except OSError:
        return ""
    return "data:image/png;base64," + base64.b64encode(dados).decode("ascii")


_QR_DATA_NORDESTE = _carregar_qr_data_nordeste()

_FONTES_BOX_INTRO_HTML = (
    '<div class="fontes-box-intro">'
    '<div class="fontes-box-intro-text">'
    '<p class="fontes-box-intro-title">Continue explorando o tema</p>'
    '<p class="fontes-box-intro-body">Escaneie ou clique no QR code ao lado para '
    "conhecer mais conteúdos do Data Nordeste sobre este tema.</p>"
    "</div>"
    f'<a class="fontes-box-intro-qr" href="{html_module.escape(_LINK_DATA_NORDESTE)}" '
    'aria-label="Conheça mais conteúdos do Data Nordeste">'
    f'<img src="{_QR_DATA_NORDESTE}" alt="QR code do Data Nordeste" width="96" height="96">'
    "</a>"
    "</div>"
)


def _normalizar_quebras_de_link(paragrafo: str) -> str:
    return re.sub(r"\]\s*\(", "](", paragrafo)


def _renderizar_badge_fonte(rotulo: str, nome: str, url: str) -> str | None:
    if not _url_is_safe(url):
        return None
    rotulo_normalizado = "Narrativa de dados" if rotulo.casefold() == "narrativa de dados" else "Painel"
    nome_normalizado = html_module.escape(re.sub(r"\s+", " ", nome).strip())
    return (
        f'<a class="fonte-badge" href="{html_module.escape(url)}">'
        f"<strong>{rotulo_normalizado}:</strong> {nome_normalizado}</a>"
    )


def _renderizar_conteudo_caixa_fontes(
    paragrafo: str,
    contexto: dict,
    namespace: str,
    safe_report: str | None,
    graficos_por_placeholder: dict[str, str] | None,
) -> list[str]:
    paragrafo = _normalizar_quebras_de_link(paragrafo)
    fragmentos: list[str] = []
    buffer_texto: list[str] = []

    def descarregar_texto() -> None:
        if not buffer_texto:
            return
        html = texto_para_html(
            "\n".join(buffer_texto),
            contexto,
            namespace=namespace,
            graficos_por_placeholder=graficos_por_placeholder,
            safe_report=safe_report,
            classe_paragrafo="theme-detail-text",
            blocos_condicionais_ja_interpretados=True,
        )
        if html:
            fragmentos.append(html)
        buffer_texto.clear()

    for linha in paragrafo.splitlines():
        linha_limpa = linha.strip()
        if not linha_limpa:
            continue

        badge_link = _BADGE_LINK.match(linha_limpa)
        if badge_link:
            badge = _renderizar_badge_fonte(*badge_link.groups())
            if badge:
                descarregar_texto()
                fragmentos.append(badge)
            continue

        narrativa = _LINHA_NARRATIVA_DADOS.match(linha_limpa)
        if narrativa:
            nome = narrativa.group(1).strip().strip("\"'“”").strip()
            if "$" not in nome:
                badge = _renderizar_badge_fonte("Narrativa de dados", nome, narrativa.group(2))
                if badge:
                    descarregar_texto()
                    fragmentos.append(badge)
            continue

        buffer_texto.append(linha)

    descarregar_texto()
    return fragmentos


# A caixa sempre mostra "Fontes" antes de "Conteúdos relacionados",
# independentemente da ordem em que os cabeçalhos aparecem no Doc.
_ORDEM_SECOES_CAIXA = ("fontes", "relacionados")


def _chave_secao_caixa(titulo_casefold: str) -> str:
    if titulo_casefold in {"conteúdos relacionados", "conteudos relacionados"}:
        return "relacionados"
    return "fontes"


def _montar_caixa_fontes(secoes: dict[str, list[str]], incluir_intro: bool) -> str:
    if not secoes:
        return ""
    corpo = "".join(
        "".join(secoes[chave]) for chave in _ORDEM_SECOES_CAIXA if chave in secoes
    )
    intro = _FONTES_BOX_INTRO_HTML if incluir_intro else ""
    # padding-top em ".fontes-box-wrap" (não margin em ".fontes-box"): margem
    # de quem começa uma página nova é descartada pelo WeasyPrint.
    return (
        '<div class="fontes-box-wrap"><div class="fontes-box">'
        + intro + corpo +
        "</div></div>"
    )


def _renderizar_secao_caixa_fontes(
    texto_da_secao: str,
    contexto: dict,
    namespace: str,
    safe_report: str | None,
    graficos_por_placeholder: dict[str, str] | None,
) -> str:
    """Monta a caixa a partir de um trecho já iniciado em "#!Fontes"/"#!Conteúdos
    relacionados". Usado quando esse conteúdo sobra para texto_para_html em vez
    de vir pelo fluxo por parágrafos de render_descricao_tema_html.
    """
    secoes: dict[str, list[str]] = {}
    secao_atual: list[str] | None = None

    for paragrafo in re.split(r"\n\s*\n", texto_da_secao):
        paragrafo = paragrafo.strip("\n\r")
        if not paragrafo:
            continue

        if paragrafo.startswith("#!"):
            titulo = paragrafo[2:].strip()
            secao_atual = secoes.setdefault(_chave_secao_caixa(titulo.casefold()), [])
            if titulo:
                secao_atual.append(
                    f'<h3 class="fontes-box-heading">{convert_links_to_html(titulo)}</h3>'
                )
            continue

        if secao_atual is None:
            secao_atual = secoes.setdefault("fontes", [])
        secao_atual.extend(
            _renderizar_conteudo_caixa_fontes(
                paragrafo, contexto, namespace, safe_report, graficos_por_placeholder
            )
        )

    return _montar_caixa_fontes(secoes, incluir_intro=True)


_CABECALHO_TITULO = re.compile(r"(?i)^#!\s*(.*)$")


def _dividir_em_segmentos_caixa_fontes(texto: str) -> list[tuple[bool, str]]:
    """Divide o texto em trechos dentro/fora de uma seção "Fontes"/"Conteúdos
    relacionados" (duas em sequência caem no mesmo trecho)."""
    segmentos: list[tuple[bool, str]] = []
    buffer: list[str] = []
    em_caixa = False

    def descarregar() -> None:
        if buffer:
            segmentos.append((em_caixa, "\n".join(buffer)))
            buffer.clear()

    for linha in texto.splitlines():
        cabecalho = _CABECALHO_TITULO.match(linha.strip())
        if cabecalho:
            novo_em_caixa = cabecalho.group(1).strip().casefold() in _SECOES_CAIXA_FONTES
            if novo_em_caixa != em_caixa:
                descarregar()
                em_caixa = novo_em_caixa
        buffer.append(linha)

    descarregar()
    return segmentos


def render_descricao_tema_html(
    descricao_tema: str,
    contexto: dict,
    namespace: str = "demografia",
    safe_report: str | None = None,
    graficos_por_placeholder: dict[str, str] | None = None,
) -> list[str]:
    # A flag de supressão é estado de módulo e sobrevive entre chamadas de
    # texto_para_html (necessário porque marcador e legenda caem em parágrafos
    # separados). Zeramos no início de cada macrotema para que uma flag deixada
    # True por um marcador órfão no fim do tema anterior não descarte, por
    # engano, a primeira legenda deste tema.
    global _suprimir_proxima_legenda
    _suprimir_proxima_legenda = False
    descricao_tema = interpretar_blocos_condicionais(descricao_tema, contexto)
    partes = []
    intro_ja_inserida = False
    secoes_caixa: dict[str, list[str]] | None = None
    secao_atual: list[str] | None = None

    def abrir_secao_caixa(titulo: str) -> None:
        nonlocal secoes_caixa, secao_atual
        if secoes_caixa is None:
            secoes_caixa = {}
        secao_atual = secoes_caixa.setdefault(_chave_secao_caixa(titulo.casefold()), [])
        secao_atual.append(f'<h3 class="fontes-box-heading">{convert_links_to_html(titulo)}</h3>')

    def fechar_caixa_fontes() -> None:
        nonlocal secoes_caixa, secao_atual, intro_ja_inserida
        if secoes_caixa:
            partes.append(_montar_caixa_fontes(secoes_caixa, incluir_intro=not intro_ja_inserida))
            intro_ja_inserida = True
        secoes_caixa = None
        secao_atual = None

    for paragrafo in re.split(r"\n\s*\n", descricao_tema):
        paragrafo = paragrafo.strip("\n\r")
        if not paragrafo:
            continue

        paragrafo = substituir_placeholders(paragrafo, contexto, namespace)

        if paragrafo.startswith("#!"):
            titulo = paragrafo[2:].strip()
            if titulo.casefold() in _SECOES_CAIXA_FONTES:
                abrir_secao_caixa(titulo)
            else:
                fechar_caixa_fontes()
                if titulo:
                    partes.append(
                        f'<h2 class="theme-detail-heading">{convert_links_to_html(titulo)}</h2>'
                    )
            continue

        if paragrafo.casefold() in _SECOES_TITULO_ESPECIAL:
            if paragrafo.casefold() in _SECOES_CAIXA_FONTES:
                abrir_secao_caixa(paragrafo)
            else:
                fechar_caixa_fontes()
                partes.append(
                    f'<h2 class="theme-detail-heading">{convert_links_to_html(paragrafo)}</h2>'
                )
            continue

        if secao_atual is not None:
            secao_atual.extend(
                _renderizar_conteudo_caixa_fontes(
                    paragrafo, contexto, namespace, safe_report, graficos_por_placeholder
                )
            )
            continue

        html = texto_para_html(
            paragrafo,
            contexto,
            namespace=namespace,
            graficos_por_placeholder=graficos_por_placeholder,
            safe_report=safe_report,
            classe_paragrafo="theme-detail-text",
            blocos_condicionais_ja_interpretados=True,
        )
        if html:
            partes.append(html)

    fechar_caixa_fontes()
    return partes


def texto_para_html(
    texto: str,
    contexto: dict,
    namespace: str = "demografia",
    graficos_por_placeholder: dict[str, str] | None = None,
    componentes_html: dict[str, str] | None = None,
    safe_report: str | None = None,
    classe_paragrafo: str = "",
    blocos_condicionais_ja_interpretados: bool = False,
) -> str:

    graficos_por_placeholder = graficos_por_placeholder or {}
    componentes_html = componentes_html or {}

    if not blocos_condicionais_ja_interpretados:
        texto = interpretar_blocos_condicionais(texto, contexto)
    texto_renderizado = substituir_placeholders(texto, contexto, namespace)

    # Seções "#!Fontes"/"#!Conteúdos relacionados" (quando sobram aqui em vez
    # de já virem isoladas por render_descricao_tema_html) são renderizadas à
    # parte, como uma caixa única, e substituídas por um marcador de linha
    # que o loop abaixo simplesmente devolve no lugar.
    caixas_por_marcador: dict[str, str] = {}
    trechos_texto: list[str] = []
    for indice, (em_caixa, texto_segmento) in enumerate(
        _dividir_em_segmentos_caixa_fontes(texto_renderizado)
    ):
        if not em_caixa:
            trechos_texto.append(texto_segmento)
            continue
        caixa_html = _renderizar_secao_caixa_fontes(
            texto_segmento, contexto, namespace, safe_report, graficos_por_placeholder
        )
        if caixa_html:
            marcador = f"\x00FONTES_BOX_{indice}\x00"
            caixas_por_marcador[marcador] = caixa_html
            trechos_texto.append(marcador)
    texto_renderizado = "\n".join(trechos_texto)

    linhas = [linha.rstrip() for linha in texto_renderizado.splitlines()]

    html_lines = []

    em_lista = False
    em_metadado_docs = False
    metadado_visivel: list[str] | None = None

    proximo_paragrafo_destaque = False

    global _suprimir_proxima_legenda

    for linha in linhas:

        linha_sem_bom = linha.lstrip("\ufeff")
        sem_tabs = linha_sem_bom.lstrip("\t")
        n_tabs = len(linha_sem_bom) - len(sem_tabs)
        sem_espacos = sem_tabs.lstrip(" ")
        n_espacos = len(sem_tabs) - len(sem_espacos)
        nivel_indentacao = n_tabs + n_espacos // 4
        linha_limpa = linha_sem_bom.strip()

        if linha_limpa in caixas_por_marcador:
            if em_lista:
                html_lines.append("</ul>")
                em_lista = False
            html_lines.append(caixas_por_marcador[linha_limpa])
            continue

        if metadado_visivel is not None:
            terminou = "@@" in linha_limpa
            conteudo = linha_limpa.split("@@", 1)[0].strip()
            if conteudo:
                metadado_visivel.append(conteudo)
            if terminou:
                texto_metadado = " ".join(metadado_visivel).strip().strip('"“”')
                if texto_metadado:
                    html_lines.append(f"<p>{convert_links_to_html(texto_metadado)}</p>")
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
                        html_lines.append(f"<p>{convert_links_to_html(texto_metadado)}</p>")
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
            r"(?:%%|\*)(\w+(?:\+\w+)*)",
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

                largura_maxima = _CONFIG_GRAFICOS.get(tipo, {}).get(
                    "largura_maxima", _LARGURA_MAXIMA_GRAFICO_PADRAO
                )

                figuras.append(
                    '<figure style="text-align:center; margin:0; flex:1; min-width:280px;">'
                    f'<img src="/output/{html_module.escape(chart_file)}" '
                    f'alt="{html_module.escape(tipo)}" '
                    f'style="width:100%; max-width:{largura_maxima}; object-fit:contain;">'
                    "</figure>"
                )

            if figuras:

                margem_vertical = next(
                    (
                        _CONFIG_GRAFICOS[tipo]["margem_vertical"]
                        for tipo in tipos
                        if tipo in _CONFIG_GRAFICOS
                    ),
                    _MARGEM_VERTICAL_GRAFICOS_PADRAO,
                )
                html_lines.append(
                    '<div style="display:flex; gap:24px; justify-content:center; '
                    f'align-items:flex-start; margin:{margem_vertical} 0; flex-wrap:wrap;">'
                    + "".join(figuras)
                    + "</div>"
                )

            _suprimir_proxima_legenda = not figuras

            continue

        # TÍTULO PRINCIPAL
        if linha_limpa.startswith("#!"):

            if em_lista:
                html_lines.append("</ul>")
                em_lista = False

            _suprimir_proxima_legenda = False
            titulo = linha_limpa[2:].strip()

            if titulo:
                html_lines.append(
                    f"<h1>{html_module.escape(titulo)}</h1>"
                )

            continue

        # LISTAS
        if linha_limpa.startswith(("- ", "• ", "* ")):

            _suprimir_proxima_legenda = False

            if not em_lista:
                html_lines.append("<ul>")
                em_lista = True

            item = convert_links_to_html(
                _substituir_referencia_figura_inline(linha_limpa[2:].strip())
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

            _suprimir_proxima_legenda = False
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

            # O gráfico desta legenda não existe para este município: descarta
            # a legenda sem consumir número, para a numeração seguir contínua.
            if _suprimir_proxima_legenda:
                _suprimir_proxima_legenda = False
                proximo_paragrafo_destaque = False
                continue

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

            _suprimir_proxima_legenda = False

            linha_limpa = re.sub(
                r"\[[A-Za-z0-9]{1,3}\]",
                "",
                linha_limpa,
            )
            linha_limpa = _substituir_referencia_figura_inline(linha_limpa)

            if classe_paragrafo:
                classe = f' class="{classe_paragrafo}"'
            elif proximo_paragrafo_destaque:
                classe = ' class="lead"'
            else:
                classe = ""

            estilo = (
                f' style="text-indent: {round(nivel_indentacao * 32, 2)}px;"'
                if nivel_indentacao
                else ""
            )

            html_lines.append(
                f"<p{classe}{estilo}>"
                f"{convert_links_to_html(linha_limpa)}"
                f"</p>"
            )

            proximo_paragrafo_destaque = False

    if em_lista:
        html_lines.append("</ul>")

    return "\n".join(html_lines)
