import html
import json
import logging
import os
import re
import unicodedata
from urllib.error import URLError, HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from config import BASE_DIR, OUTPUT_DIR

logger = logging.getLogger(__name__)

GEOCODING_CACHE_FILE = OUTPUT_DIR / "geocoding_cache.json"
BRASIL_ESTADOS_SOURCE_ASSET = "brazil-states.svg"
BRASIL_ESTADOS_OUTPUT_ASSET = "brazil-states-regions.svg"
BRASIL_ESTADOS_SOURCE = BASE_DIR / "assets" / BRASIL_ESTADOS_SOURCE_ASSET
BRASIL_ESTADOS_OUTPUT = OUTPUT_DIR / BRASIL_ESTADOS_OUTPUT_ASSET
MAP_SHAPE_DIR = BASE_DIR / "map_shape"
MUNICIPIOS_SHAPE = MAP_SHAPE_DIR / "BR_Municipios_2025" / "BR_Municipios_2025.shp"
UF_SHAPE = MAP_SHAPE_DIR / "BR_UF_2025" / "BR_UF_2025.shp"
REGIAO_CORES_POR_CLASSE = {
    "fil4": "#079342",  # Norte
    "fil5": "#a55596",  # Centro-Oeste
    "fil6": "#d72b24",  # Sudeste
    "fil7": "#f0c70d",  # Sul
    "fil8": "#2e98cf",  # Nordeste
}

_MUNICIPIOS_GDF = None
_UF_GDF = None
REGIOES_LEGENDA = [
    ("Norte", "#079342"),
    ("Nordeste", "#2e98cf"),
    ("Centro-Oeste", "#a55596"),
    ("Sudeste", "#d72b24"),
    ("Sul", "#f0c70d"),
]
UF_NOMES = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AM": "Amazonas",
    "AP": "Amapá",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MG": "Minas Gerais",
    "MS": "Mato Grosso do Sul",
    "MT": "Mato Grosso",
    "PA": "Pará",
    "PB": "Paraíba",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "PR": "Paraná",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RO": "Rondônia",
    "RR": "Roraima",
    "RS": "Rio Grande do Sul",
    "SC": "Santa Catarina",
    "SE": "Sergipe",
    "SP": "São Paulo",
    "TO": "Tocantins",
}

BRASIL_BOUNDS = {
    "south": -34.0,
    "north": 5.6,
    "west": -74.2,
    "east": -32.0,
}
BRASIL_MAP_VIEWBOX = {
    "width": 220000,
    "height": 194010,
}
BRASIL_MAP_BBOX = {
    "x_min": 5710,
    "x_max": 191363,
    "y_min": 1639,
    "y_max": 192212,
}
ESTADOS_COORDENADAS = {
    "AC": (-70.3, -9.0),
    "AL": (-36.7, -9.7),
    "AM": (-63.5, -4.5),
    "AP": (-51.8, 1.2),
    "BA": (-41.7, -12.7),
    "CE": (-39.5, -5.2),
    "DF": (-47.8, -15.8),
    "ES": (-40.4, -19.7),
    "GO": (-49.8, -16.0),
    "MA": (-45.3, -5.0),
    "MG": (-44.5, -18.5),
    "MS": (-54.5, -20.5),
    "MT": (-56.0, -13.0),
    "PA": (-52.5, -4.0),
    "PB": (-36.6, -7.1),
    "PE": (-37.8, -8.4),
    "PI": (-42.5, -7.5),
    "PR": (-51.5, -24.8),
    "RJ": (-43.3, -22.3),
    "RN": (-36.6, -5.8),
    "RO": (-63.0, -10.9),
    "RR": (-61.4, 1.9),
    "RS": (-53.0, -30.0),
    "SC": (-50.5, -27.3),
    "SE": (-37.3, -10.6),
    "SP": (-48.5, -22.5),
    "TO": (-48.3, -10.2),
}


def separar_cidade_uf(nome_municipio: str) -> tuple[str, str]:
    nome = str(nome_municipio).strip()
    if nome.endswith(")") and "(" in nome:
        cidade, uf = nome.rsplit("(", 1)
        return cidade.strip(), uf.rstrip(")").strip().upper()
    return nome, ""


def normalizar_texto(valor: object) -> str:
    texto = str(valor or "").strip().casefold()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(char for char in texto if not unicodedata.combining(char))


def carregar_malhas():
    global _MUNICIPIOS_GDF, _UF_GDF

    if _MUNICIPIOS_GDF is None or _UF_GDF is None:
        import geopandas as gpd

        _MUNICIPIOS_GDF = gpd.read_file(MUNICIPIOS_SHAPE)
        _UF_GDF = gpd.read_file(UF_SHAPE)

    return _MUNICIPIOS_GDF, _UF_GDF


def localizar_municipio(nome_municipio: str):
    municipios, _ufs = carregar_malhas()
    cidade, uf = separar_cidade_uf(nome_municipio)
    cidade_normalizada = normalizar_texto(cidade)

    filtro = municipios["NM_MUN"].map(normalizar_texto) == cidade_normalizada
    if uf:
        filtro = filtro & (municipios["SIGLA_UF"].astype(str).str.upper() == uf)

    encontrados = municipios.loc[filtro]
    if encontrados.empty:
        return None

    return encontrados.iloc[0]


def expandir_bounds(bounds, fator: float = 0.12) -> tuple[float, float, float, float]:
    minx, miny, maxx, maxy = bounds
    largura = max(maxx - minx, 0.08)
    altura = max(maxy - miny, 0.08)
    return (
        minx - largura * fator,
        maxx + largura * fator,
        miny - altura * fator,
        maxy + altura * fator,
    )


def bounds_por_pontos_principais(gdf, alvo=None, fator: float = 0.08) -> tuple[float, float, float, float]:
    pontos = gdf.geometry.representative_point()
    minx = pontos.x.quantile(0.02)
    maxx = pontos.x.quantile(0.98)
    miny = pontos.y.quantile(0.02)
    maxy = pontos.y.quantile(0.98)

    if alvo is not None:
        alvo_minx, alvo_miny, alvo_maxx, alvo_maxy = alvo.geometry.bounds
        minx = min(minx, alvo_minx)
        maxx = max(maxx, alvo_maxx)
        miny = min(miny, alvo_miny)
        maxy = max(maxy, alvo_maxy)

    return expandir_bounds((minx, miny, maxx, maxy), fator)


def ampliar_altura_bounds(bounds, proporcao_altura_largura: float = 1.25) -> tuple[float, float, float, float]:
    minx, maxx, miny, maxy = bounds
    largura = maxx - minx
    altura = maxy - miny
    altura_desejada = largura * proporcao_altura_largura

    if altura >= altura_desejada:
        return bounds

    centro_y = (miny + maxy) / 2
    return (minx, maxx, centro_y - altura_desejada / 2, centro_y + altura_desejada / 2)


def configurar_eixo_mapa(ax, bounds=None) -> None:
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    if bounds is not None:
        minx, maxx, miny, maxy = bounds
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)


def formatar_grau_decimal(valor: float, eixo: str) -> str:
    hemisferio = "W" if eixo == "lon" and valor < 0 else "E" if eixo == "lon" else "S" if valor < 0 else "N"
    absoluto = abs(valor)
    graus = int(absoluto)
    minutos = int(round((absoluto - graus) * 60))
    if minutos == 60:
        graus += 1
        minutos = 0
    return f"{graus}°{minutos}'{hemisferio}"


def ticks_intervalo(minimo: float, maximo: float, quantidade: int) -> list[float]:
    if quantidade <= 1:
        return [(minimo + maximo) / 2]
    passo = (maximo - minimo) / (quantidade - 1)
    return [minimo + passo * indice for indice in range(quantidade)]


def aplicar_grade_coordenadas(ax, bounds, x_ticks=None, y_ticks=None, fontsize: float = 6.0) -> None:
    minx, maxx, miny, maxy = bounds
    x_ticks = x_ticks or ticks_intervalo(minx, maxx, 3)
    y_ticks = y_ticks or ticks_intervalo(miny, maxy, 4)

    ax.set_xticks(x_ticks)
    ax.set_yticks(y_ticks)
    ax.set_xticklabels([formatar_grau_decimal(tick, "lon") for tick in x_ticks], fontsize=fontsize)
    ax.set_yticklabels([formatar_grau_decimal(tick, "lat") for tick in y_ticks], fontsize=fontsize, rotation=90, va="center")
    ax.tick_params(
        axis="x",
        top=True,
        labeltop=True,
        bottom=True,
        labelbottom=False,
        length=2.5,
        pad=1,
        colors="#1f1f1f",
    )
    ax.tick_params(
        axis="y",
        right=True,
        labelright=True,
        left=True,
        labelleft=False,
        length=2.5,
        pad=1,
        colors="#1f1f1f",
    )


def desenhar_escala(ax, km_total: int, pos=(0.70, 0.055), largura_frac: float = 0.16, fontsize: float = 5.5) -> None:
    x0, y0 = pos
    x1 = x0 + largura_frac
    x_mid = x0 + largura_frac / 2
    ax.plot([x0, x1], [y0, y0], transform=ax.transAxes, color="#111", lw=0.9, clip_on=False)
    for x in [x0, x_mid, x1]:
        ax.plot([x, x], [y0, y0 - 0.018], transform=ax.transAxes, color="#111", lw=0.9, clip_on=False)
    ax.text(x0, y0 + 0.012, "0", transform=ax.transAxes, ha="center", va="bottom", fontsize=fontsize, color="#111")
    ax.text(x_mid, y0 + 0.012, f"{km_total // 2}", transform=ax.transAxes, ha="center", va="bottom", fontsize=fontsize, color="#111")
    ax.text(x1 + 0.012, y0 + 0.012, f"{km_total} km", transform=ax.transAxes, ha="left", va="bottom", fontsize=fontsize, color="#111")


def desenhar_nomes_ufs(ax, ufs, bounds, alvo_uf: str, fontsize: float = 7.0) -> None:
    import matplotlib.patheffects as path_effects

    minx, maxx, miny, maxy = bounds
    visiveis = ufs.cx[minx:maxx, miny:maxy]
    for _, estado in visiveis.iterrows():
        sigla = str(estado["SIGLA_UF"]).upper()
        ponto = estado.geometry.representative_point()
        if not (minx <= ponto.x <= maxx and miny <= ponto.y <= maxy):
            continue
        margem_x = (maxx - minx) * 0.055
        margem_y = (maxy - miny) * 0.055
        texto_x = min(max(ponto.x, minx + margem_x), maxx - margem_x)
        texto_y = min(max(ponto.y, miny + margem_y), maxy - margem_y)
        ax.text(
            texto_x,
            texto_y,
            sigla,
            fontsize=fontsize,
            color="white",
            fontweight="bold",
            ha="center",
            va="center",
            path_effects=[path_effects.withStroke(linewidth=1.2, foreground="#575757")],
        )


def anotar_municipios_vizinhos(ax, municipios, alvo, limite: int = 9) -> None:
    municipios_metrico = municipios.to_crs(epsg=3857)
    alvo_metrico = municipios.loc[[alvo.name]].to_crs(epsg=3857).iloc[0]
    centro_alvo = alvo_metrico.geometry.representative_point()
    municipios = municipios.copy()
    municipios["_distancia"] = municipios_metrico.geometry.representative_point().distance(centro_alvo).values
    vizinhos = municipios.sort_values("_distancia").head(limite)

    for _, municipio in vizinhos.iterrows():
        ponto = municipio.geometry.representative_point()
        ax.text(
            ponto.x,
            ponto.y,
            str(municipio["NM_MUN"]),
            fontsize=4.8,
            color="#5e5245",
            ha="center",
            va="center",
        )


def desenhar_norte(ax, fontsize: float = 8.0, pos=(0.94, 0.9)) -> None:
    x, y = pos
    ax.annotate(
        "N",
        xy=(x, y),
        xytext=(x, y - 0.105),
        xycoords="axes fraction",
        textcoords="axes fraction",
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight="bold",
        arrowprops={"arrowstyle": "-|>", "color": "#262626", "lw": 1},
    )


def gerar_mapa_regiao(nome_municipio: str, safe_report: str) -> str | None:
    try:
        municipios, ufs = carregar_malhas()
        municipio = localizar_municipio(nome_municipio)
    except Exception as e:
        logger.warning("Falha ao carregar malhas ou localizar município '%s': %s", nome_municipio, e)
        return None

    if municipio is None:
        logger.warning("Município '%s' não encontrado nas malhas shapefile", nome_municipio)
        return None

    os.environ.setdefault("MPLCONFIGDIR", str(OUTPUT_DIR / "matplotlib-cache"))
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"mapa_regiao_{safe_report}.png"

    uf = str(municipio["SIGLA_UF"]).upper()
    nome_uf = UF_NOMES.get(uf, uf)
    nome_cidade = str(municipio["NM_MUN"])
    municipios_uf = municipios[municipios["SIGLA_UF"].astype(str).str.upper() == uf]
    uf_alvo = ufs[ufs["SIGLA_UF"].astype(str).str.upper() == uf]
    municipio_gdf = municipios.loc[[municipio.name]]

    cinza = "#9a9a9a"
    municipio_cor = "#f5822a"
    uf_cor = "#f8cd8b"
    fundo_cor = "#ffd18f"
    limite_cor = "#6b604f"

    fig = plt.figure(figsize=(8.3, 5.55), facecolor="white")
    grid = fig.add_gridspec(1, 2, width_ratios=[1, 1], wspace=0.05)
    ax_estado = fig.add_subplot(grid[0])
    ax_cidade = fig.add_subplot(grid[1])

    estado_bounds = ampliar_altura_bounds(
        bounds_por_pontos_principais(municipios_uf, municipio, 0.42),
        1.25,
    )
    ax_estado.set_facecolor("#d8e9f7")
    configurar_eixo_mapa(ax_estado, estado_bounds)
    ufs.plot(ax=ax_estado, color=cinza, edgecolor="#202020", linewidth=0.55)
    municipios_uf.plot(ax=ax_estado, color=uf_cor, edgecolor="#b78347", linewidth=0.24)
    ufs.boundary.plot(ax=ax_estado, color="#202020", linewidth=0.55)
    uf_alvo.boundary.plot(ax=ax_estado, color="#202020", linewidth=0.65)
    municipio_gdf.plot(ax=ax_estado, color=municipio_cor, edgecolor="#8a3d12", linewidth=0.7)
    aplicar_grade_coordenadas(ax_estado, estado_bounds, fontsize=5.4)
    desenhar_nomes_ufs(ax_estado, ufs, estado_bounds, uf, fontsize=7.0)
    desenhar_norte(ax_estado, fontsize=7.5, pos=(0.94, 0.91))
    desenhar_escala(ax_estado, 200, pos=(0.61, 0.06), largura_frac=0.28, fontsize=5.1)

    ax_cidade.set_facecolor(fundo_cor)
    municipios_uf.plot(ax=ax_cidade, color="#ffd79d", edgecolor="#c2955f", linewidth=0.35)
    municipio_gdf.plot(ax=ax_cidade, color=municipio_cor, edgecolor="#8a3d12", linewidth=1)
    bounds_cidade = expandir_bounds(municipio.geometry.bounds, 0.75)
    configurar_eixo_mapa(ax_cidade, bounds_cidade)
    aplicar_grade_coordenadas(ax_cidade, bounds_cidade, fontsize=5.4)
    anotar_municipios_vizinhos(ax_cidade, municipios_uf, municipio)
    desenhar_norte(ax_cidade, fontsize=8.5, pos=(0.96, 0.93))
    desenhar_escala(ax_cidade, 6, pos=(0.845, 0.055), largura_frac=0.13, fontsize=5.2)

    for ax in [ax_estado, ax_cidade]:
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color(limite_cor)
            spine.set_linewidth(0.45)

    legendas = [
        Patch(facecolor=municipio_cor, edgecolor="#8a3d12", label=nome_cidade),
        Patch(facecolor="#f6f6f6", edgecolor="#8a8a8a", label="Limites municipais"),
        Patch(facecolor=uf_cor, edgecolor="#424242", label=nome_uf),
        Patch(facecolor=cinza, edgecolor="#424242", label="Brasil"),
    ]
    ax_cidade.legend(
        handles=legendas,
        loc="lower left",
        bbox_to_anchor=(0.01, 0.075),
        fontsize=5.4,
        frameon=True,
        framealpha=0.92,
        borderpad=0.28,
        handlelength=1.2,
    )
    ax_cidade.text(
        0.015,
        0.012,
        "Sistema de Coordenadas: Geográfico\nSistema Geodésico de Referência: SIRGAS 2000",
        transform=ax_cidade.transAxes,
        fontsize=5.0,
        color="#5d5146",
        ha="left",
        va="bottom",
    )
    fig.subplots_adjust(left=0.015, right=0.995, top=0.965, bottom=0.018)
    fig.savefig(chart_file, dpi=190, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return chart_file.name


def carregar_cache_geocoding() -> dict:
    if not GEOCODING_CACHE_FILE.exists():
        return {}

    try:
        return json.loads(GEOCODING_CACHE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def salvar_cache_geocoding(cache: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    GEOCODING_CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def montar_bounds_aproximado(lat: float, lon: float) -> dict[str, float]:
    margem = 1.6
    return {
        "south": lat - margem,
        "north": lat + margem,
        "west": lon - margem,
        "east": lon + margem,
    }


def normalizar_resultado_geocoding(dados: dict) -> dict[str, object]:
    lat = float(dados["lat"])
    lon = float(dados["lon"])
    bounds = dados.get("bounds")

    if not bounds:
        bounds = montar_bounds_aproximado(lat, lon)

    return {"lat": lat, "lon": lon, "bounds": bounds}


def garantir_asset_mapa_estados() -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if BRASIL_ESTADOS_SOURCE.exists():
        svg = BRASIL_ESTADOS_SOURCE.read_text(encoding="utf-8")
        svg = colorir_mapa_por_regiao(svg)
        BRASIL_ESTADOS_OUTPUT.write_text(svg, encoding="utf-8")
    return f"/output/{BRASIL_ESTADOS_OUTPUT_ASSET}"


def colorir_mapa_por_regiao(svg: str) -> str:
    def trocar_fill(match: re.Match) -> str:
        tag = match.group(0)
        classe = re.search(r'class="([^"]+)"', tag)

        if not classe:
            return tag

        classes = set(classe.group(1).split())
        cor = next(
            (cor for classe_regiao, cor in REGIAO_CORES_POR_CLASSE.items() if classe_regiao in classes),
            None,
        )

        if not cor:
            return tag

        if "fill:#b3b3b3" in tag:
            tag = tag.replace("fill:#b3b3b3", f"fill:{cor}")
        elif "fill:#B3B3B3" in tag:
            tag = tag.replace("fill:#B3B3B3", f"fill:{cor}")

        return tag

    return re.sub(r"<path\b[^>]*>", trocar_fill, svg)


def projetar_ponto_percentual(lon: float, lat: float) -> tuple[float, float]:
    bounds = BRASIL_BOUNDS
    mapa = BRASIL_MAP_BBOX
    viewbox = BRASIL_MAP_VIEWBOX
    x_svg = mapa["x_min"] + ((lon - bounds["west"]) / (bounds["east"] - bounds["west"])) * (
        mapa["x_max"] - mapa["x_min"]
    )
    y_svg = mapa["y_min"] + ((bounds["north"] - lat) / (bounds["north"] - bounds["south"])) * (
        mapa["y_max"] - mapa["y_min"]
    )
    x = (x_svg / viewbox["width"]) * 100
    y = (y_svg / viewbox["height"]) * 100
    return x, y


def render_svg_localizador(cidade: str, lat: float, lon: float) -> str:
    ponto_x, ponto_y = projetar_ponto_percentual(lon, lat)
    cidade_segura = html.escape(cidade)
    asset_url = html.escape(garantir_asset_mapa_estados())
    labels_estados = []

    for sigla, (estado_lon, estado_lat) in ESTADOS_COORDENADAS.items():
        estado_x, estado_y = projetar_ponto_percentual(estado_lon, estado_lat)
        labels_estados.append(
            f'<span class="state-label" style="left: {estado_x:.2f}%; top: {estado_y:.2f}%;">'
            f'{sigla}'
            '</span>'
        )

    return (
        f'<img class="locator-map" src="{asset_url}" alt="Mapa do Brasil com divisões estaduais">'
        f'{"".join(labels_estados)}'
        f'<span class="locator-label" style="left: {ponto_x:.2f}%; top: {ponto_y:.2f}%;">'
        f'{cidade_segura}'
        '</span>'
        f'<span class="locator-dot" style="left: {ponto_x:.2f}%; top: {ponto_y:.2f}%;" '
        f'aria-label="Localização de {cidade_segura}"></span>'
    )


def render_legenda_regioes() -> str:
    itens = []
    for nome, cor in REGIOES_LEGENDA:
        nome_seguro = html.escape(nome)
        itens.append(
            '<span class="region-legend-item">'
            f'<span class="region-legend-swatch" style="background: {cor};"></span>'
            f'{nome_seguro}'
            '</span>'
        )
    return f'<div class="region-legend">{"".join(itens)}</div>'


def geocodificar_municipio(nome_municipio: str) -> dict[str, object] | None:
    cidade, uf = separar_cidade_uf(nome_municipio)
    cache_key = f"{cidade} ({uf})" if uf else cidade
    cache = carregar_cache_geocoding()

    if cache_key in cache:
        return normalizar_resultado_geocoding(cache[cache_key])

    query = ", ".join(parte for parte in [cidade, uf, "Brasil"] if parte)
    params = urlencode({"format": "jsonv2", "limit": "1", "q": query})
    request = Request(
        f"https://nominatim.openstreetmap.org/search?{params}",
        headers={
            "User-Agent": "Automatic-Reporting/1.0 (municipal report generator)",
        },
    )

    try:
        with urlopen(request, timeout=12) as response:
            resultados = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None

    if not resultados:
        return None

    lat = float(resultados[0]["lat"])
    lon = float(resultados[0]["lon"])
    boundingbox = resultados[0].get("boundingbox", [])
    bounds = None

    if len(boundingbox) == 4:
        bounds = {
            "south": float(boundingbox[0]),
            "north": float(boundingbox[1]),
            "west": float(boundingbox[2]),
            "east": float(boundingbox[3]),
        }

    cache[cache_key] = {
        "lat": lat,
        "lon": lon,
        "bounds": bounds or montar_bounds_aproximado(lat, lon),
    }
    salvar_cache_geocoding(cache)
    return normalizar_resultado_geocoding(cache[cache_key])


def montar_url_busca_mapa(nome_municipio: str) -> str:
    return f"https://www.openstreetmap.org/search?query={quote(nome_municipio)}"


def render_mapa_geografico(contexto: dict) -> str:
    nome_municipio = str(contexto.get("nm_mun", "")).strip()
    cidade, uf = separar_cidade_uf(nome_municipio)
    nome_seguro = html.escape(nome_municipio)
    cidade_segura = html.escape(cidade)
    mapa = geocodificar_municipio(nome_municipio)

    if mapa:
        lat = float(mapa["lat"])
        lon = float(mapa["lon"])
        return (
            '<figure class="map-block">'
            f'<div class="map-title">Localização de {cidade_segura} no Brasil</div>'
            '<div class="map-frame">'
            f'{render_svg_localizador(cidade, lat, lon)}'
            '</div>'
            f'{render_legenda_regioes()}'
            f'<figcaption>Localização de {cidade_segura} no Brasil</figcaption>'
            '</figure>'
        )

    busca_url = html.escape(montar_url_busca_mapa(nome_municipio))
    return (
        '<figure class="map-block map-block--fallback">'
        '<div class="map-fallback">'
        f'<strong>{nome_seguro}</strong>'
        '<span>Mapa geográfico indisponível no momento.</span>'
        f'<a href="{busca_url}" target="_blank" rel="noopener noreferrer">Abrir no OpenStreetMap</a>'
        '</div>'
        f'<figcaption>Mapa de localização de {nome_seguro}.</figcaption>'
        '</figure>'
    )
