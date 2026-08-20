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
