import logging
import re

import httpx

from config import get_config_value

logger = logging.getLogger(__name__)

CONTENTFUL_SPACE_ID = get_config_value("CONTENTFUL_SPACE_ID")
CONTENTFUL_ACCESS_TOKEN = get_config_value("CONTENTFUL_ACCESS_TOKEN")
CONTENTFUL_ENVIRONMENT = get_config_value("CONTENTFUL_ENVIRONMENT") or "master"


def separar_cidade_uf(nome_municipio: str) -> tuple[str, str]:
    nome = nome_municipio.strip()
    if "(" in nome:
        cidade, uf = nome.rsplit("(", 1)
        return cidade.strip(), uf.rstrip(")").strip().upper()
    return nome_municipio, ""


def slugificar(texto: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", texto.strip().lower())


def obter_url_mapa_contentful(nome_municipio: str) -> str | None:
    if not CONTENTFUL_SPACE_ID or not CONTENTFUL_ACCESS_TOKEN:
        return None

    cidade, uf = separar_cidade_uf(nome_municipio)
    if not cidade:
        return None

    partes = [slugificar(cidade)]
    if uf:
        partes.append(uf.lower())
    asset_title = f"mapa_regiao_todos__{'_'.join(partes)}.png"

    url = (
        f"https://cdn.contentful.com/spaces/{CONTENTFUL_SPACE_ID}/assets"
        f"?access_token={CONTENTFUL_ACCESS_TOKEN}"
        f"&fields.title={asset_title}&limit=1"
    )

    try:
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if items:
            file_url = items[0].get("fields", {}).get("file", {}).get("url", "")
            if file_url:
                return f"https:{file_url}" if file_url.startswith("//") else file_url
    except (httpx.HTTPError, KeyError, TypeError, AttributeError, ValueError) as e:
        logger.debug("Conteúdo inesperado ao extrair URL do Contentful: %s", e)

    return None
