from fastapi import HTTPException

from utils.data.macrotemas import MACROTEMAS, TODOS_MACROTEMAS_SLUG


def get_macrotema(slug: str) -> dict[str, str]:
    macrotema = MACROTEMAS.get(slug)
    if not macrotema:
        validos = ", ".join([TODOS_MACROTEMAS_SLUG, *MACROTEMAS.keys()])
        raise HTTPException(status_code=400, detail=f"Macrotema inválido. Use um destes: {validos}")
    return macrotema


def get_macrotema_slugs_para_relatorio(macrotema: str) -> list[str]:
    if macrotema == TODOS_MACROTEMAS_SLUG:
        return list(MACROTEMAS.keys())
    slugs = [slug.strip() for slug in macrotema.split(",") if slug.strip()]
    if not slugs:
        return ["demografia"]
    slugs_unicos: list[str] = []
    for slug in slugs:
        if slug == TODOS_MACROTEMAS_SLUG:
            return list(MACROTEMAS.keys())
        get_macrotema(slug)
        if slug not in slugs_unicos:
            slugs_unicos.append(slug)
    return slugs_unicos