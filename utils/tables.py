import html as html_module

STATUS_MAP = {
    "critico": {
        "label": "Atenção prioritária",
        "cor": "#c0392b",
        "bg": "#fbeaea",
    },
    "moderado": {
        "label": "Atenção moderada",
        "cor": "#d4a017",
        "bg": "#fdf3d7",
    },
    "positivo": {
        "label": "Atenção regular",
        "cor": "#2e7d32",
        "bg": "#e8f5e9",
    },
}


MACROTEMA_CONFIG = {
    "demografia": {
        "tema": "Demografia",
        "indicadores": "População residente · Variação populacional · Sexo, idade, cor/raça",
        "paineis": "Perfil Demográfico",
        "calcular_status": lambda ctx: _status_demografia(ctx),
    },
    "educacao": {
        "tema": "Educação",
        "indicadores": "Taxa de alfabetização (15+) · Distribuição por grau de instrução · Analfabetismo por faixa etária",
        "paineis": "Analfabetismo\nNível de Instrução",
        "calcular_status": lambda ctx: ("moderado", "Sem dados disponíveis"),
    },
    "saude": {
        "tema": "Saúde",
        "indicadores": "Cobertura vacinal · Mortalidade infantil · Estabelecimentos de saúde",
        "paineis": "Imunização\nMortalidade Infantil\nEstabelecimentos de Saúde",
        "calcular_status": lambda ctx: ("positivo", "Sem dados disponíveis"),
    },
    "economia-renda": {
        "tema": "Economia e Renda",
        "indicadores": "PIB total e per capita · Composição setorial do VAB · Comércio exterior",
        "paineis": "PIB\nExportação\nImportação\nExportação vs Importação",
        "calcular_status": lambda ctx: ("critico", "Sem dados disponíveis"),
    },
    "saneamento": {
        "tema": "Infraestrutura e Saneamento",
        "indicadores": "Coleta de lixo · Esgotamento sanitário · Acesso à energia elétrica",
        "paineis": "Domicílios por destino de lixo\nDomicílios por tipo de esgotamento sanitário",
        "calcular_status": lambda ctx: ("critico", "Sem dados disponíveis"),
    },
    "hidraulica": {
        "tema": "Segurança Hídrica",
        "indicadores": "Cisternas e tecnologias sociais · Distribuição por finalidade · Evolução temporal do programa",
        "paineis": "Cisternas",
        "calcular_status": lambda ctx: ("positivo", "Sem dados disponíveis"),
    },
}


def _status_demografia(ctx: dict) -> tuple[str, str]:
    raw = (
        str(ctx.get("cres_pop", "0"))
        .replace("%", "")
        .replace(",", ".")
        .strip()
    )

    try:
        cres_pop = float(raw)

    except ValueError:
        cres_pop = 0.0

    if cres_pop < -5:
        status_key = "critico"

    elif cres_pop < 0:
        status_key = "moderado"

    else:
        status_key = "positivo"

    descricao = (
        f"Variação populacional de "
        f"{cres_pop:+.1f}% na década"
    )

    return status_key, descricao


def _render_paineis(texto: str) -> str:

    linhas = [
        linha.strip()
        for linha in texto.strip().splitlines()
        if linha.strip()
    ]

    if not linhas:
        return ""

    primeiro = html_module.escape(linhas[0])

    resto = "".join(
        f"<br><em>{html_module.escape(linha)}</em>"
        for linha in linhas[1:]
    )

    return f"<em>{primeiro}</em>{resto}"


def render_tabela_resumo(
    contexto: dict,
    namespace: str,
) -> str:

    config = MACROTEMA_CONFIG.get(namespace)

    if not config:
        return ""

    status_key, descricao = config["calcular_status"](contexto)

    status = STATUS_MAP[status_key]

    tema = html_module.escape(config["tema"])

    indicadores = html_module.escape(
        config["indicadores"]
    )

    paineis_html = _render_paineis(
        config["paineis"]
    )

    label = html_module.escape(
        status["label"]
    )

    descricao_esc = html_module.escape(
        descricao
    )

    cor = status["cor"]

    bg = status["bg"]

    return f'''
        <table class="summary-table" style="width:100%; border-collapse:collapse; font-family:Arial,sans-serif; font-size:13px;">
            <thead>
                <tr style="background:#f5f0e8; text-align:left;">
                    <th style="padding:8px 12px; color:#5a4a1a; font-weight:600; width:15%;">TEMA</th>
                    <th style="padding:8px 12px; color:#5a4a1a; font-weight:600; width:35%;">INDICADORES PRINCIPAIS</th>
                    <th style="padding:8px 12px; color:#5a4a1a; font-weight:600; width:25%;">PAINÉIS DATANE</th>
                    <th style="padding:8px 12px; color:#5a4a1a; font-weight:600; width:25%;">STATUS</th>
                </tr>
            </thead>

            <tbody>
                <tr style="border-left: 4px solid {cor};">

                    <td style="padding:10px 12px; color:#5a4a1a; font-size:15px;">
                        {tema}
                    </td>

                    <td style="padding:10px 12px; color:#333;">
                        {indicadores}
                    </td>

                    <td style="padding:10px 12px; color:#555;">
                        {paineis_html}
                    </td>

                    <td style="padding:10px 12px;">
                        <div style="background:{bg}; color:{cor}; padding:8px 10px; border-radius:4px; font-size:12px; line-height:1.5;">
                            ● <strong>{label}</strong><br>
                            <span>{descricao_esc}</span>
                        </div>
                    </td>

                </tr>
            </tbody>
        </table>
    '''