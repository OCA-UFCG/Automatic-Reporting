from config import get_config_value
from utils.data.macrotemas import (
    MACROTEMAS,
    TODOS_MACROTEMAS_ORDEM,
    TODOS_MACROTEMAS_SLUG,
    Macrotema,
)


def get_macrotema(slug: str) -> Macrotema:
    macrotema = MACROTEMAS.get(slug)
    if not macrotema:
        validos = ", ".join([TODOS_MACROTEMAS_SLUG, *MACROTEMAS.keys()])
        raise ValueError(f"Macrotema inválido. Use um destes: {validos}")
    return macrotema


def get_macrotema_slugs_para_relatorio(macrotema: str) -> list[str]:
    if macrotema == TODOS_MACROTEMAS_SLUG:
        return TODOS_MACROTEMAS_ORDEM.copy()
    slugs = [slug.strip() for slug in macrotema.split(",") if slug.strip()]
    if not slugs:
        raise ValueError("Macrotema não informado ou inválido.")
    slugs_unicos: list[str] = []
    for slug in slugs:
        if slug == TODOS_MACROTEMAS_SLUG:
            return TODOS_MACROTEMAS_ORDEM.copy()
        get_macrotema(slug)
        if slug not in slugs_unicos:
            slugs_unicos.append(slug)
    return slugs_unicos


def docs_env(slug: str, unidade: str = "municipio") -> str:
    """Nome da variável de ambiente com o Doc do tema na unidade. Um Doc por tema e
    unidade (André, 03/11/2026): DEMOGRAFIA_DOCS_URL → DEMOGRAFIA_ESTADO_DOCS_URL.
    Lista oficial dos nomes: .env.example."""
    env = get_macrotema(slug)["docs_env"]
    return env if unidade == "municipio" else env.replace("_DOCS_URL", f"_{unidade.upper()}_DOCS_URL")


def docs_url(slug: str, unidade: str = "municipio") -> str | None:
    if unidade == "municipio":
        return get_macrotema(slug).get("docs_url")
    # Lido na hora, e não em config.py: um Doc novo de unidade entra só pelo .env.
    return get_config_value(docs_env(slug, unidade))
