import html
import json
import re
from urllib.error import URLError, HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from config import BASE_DIR, OUTPUT_DIR


GEOCODING_CACHE_FILE = OUTPUT_DIR / "geocoding_cache.json"
BRASIL_ESTADOS_SOURCE_ASSET = "brazil-states.svg"
BRASIL_ESTADOS_OUTPUT_ASSET = "brazil-states-regions.svg"
BRASIL_ESTADOS_SOURCE = BASE_DIR / "assets" / BRASIL_ESTADOS_SOURCE_ASSET
BRASIL_ESTADOS_OUTPUT = OUTPUT_DIR / BRASIL_ESTADOS_OUTPUT_ASSET
REGIAO_CORES_POR_CLASSE = {
    "fil4": "#079342",  # Norte
    "fil5": "#a55596",  # Centro-Oeste
    "fil6": "#d72b24",  # Sudeste
    "fil7": "#f0c70d",  # Sul
    "fil8": "#2e98cf",  # Nordeste
}
REGIOES_LEGENDA = [
    ("Norte", "#079342"),
    ("Nordeste", "#2e98cf"),
    ("Centro-Oeste", "#a55596"),
    ("Sudeste", "#d72b24"),
    ("Sul", "#f0c70d"),
]

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
