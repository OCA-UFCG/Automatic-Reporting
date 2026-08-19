import os
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from config import OUTPUT_DIR
from utils.data.macrotemas import (
    MACROTEMAS,
    TODOS_MACROTEMAS_NOME,
    TODOS_MACROTEMAS_SLUG,
)


def _extrair_slugs_macrotemas(texto: str) -> list[str] | None:
    slugs_ordenados = sorted(MACROTEMAS, key=len, reverse=True)
    slugs: list[str] = []
    restante = texto
    while restante:
        slug = next((s for s in slugs_ordenados if restante.startswith(s)), None)
        if slug is None:
            return None
        slugs.append(slug)
        restante = restante[len(slug):]
        if restante:
            if not restante.startswith("_"):
                return None
            restante = restante[1:]
    return slugs


def listar_relatorios_handler():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    relatorios = []

    with os.scandir(OUTPUT_DIR) as it:
        for entrada in it:
            if not entrada.name.startswith("relatorio_") or not entrada.name.endswith(".pdf"):
                continue

            nome_base = entrada.name.removesuffix(".pdf")
            html_file = OUTPUT_DIR / f"{nome_base}.html"
            slug_completo = nome_base.replace("relatorio_", "", 1)
            mapa_file = OUTPUT_DIR / f"mapa_regiao_{slug_completo}.png"

            stat = entrada.stat()
            # use a fixed local timezone to present dates consistently across deployments
            local_tz = ZoneInfo("America/Fortaleza")
            criado_em = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).astimezone(local_tz)
            pdf_version = stat.st_mtime_ns
            html_version = html_file.stat().st_mtime_ns if html_file.exists() else None
            mapa_version = mapa_file.stat().st_mtime_ns if mapa_file.exists() else None

            macrotema = "Demografia"
            if "__" in slug_completo:
                primeira_parte, restante = slug_completo.split("__", 1)
                if primeira_parte == TODOS_MACROTEMAS_SLUG:
                    slug_cidade = restante
                    macrotema = TODOS_MACROTEMAS_NOME
                else:
                    slugs_encontrados = _extrair_slugs_macrotemas(primeira_parte)
                    if slugs_encontrados and "_".join(slugs_encontrados) == primeira_parte:
                        slug_cidade = restante
                        macrotema = ", ".join(
                            MACROTEMAS[slug]["nome"] for slug in slugs_encontrados
                        )
                    elif primeira_parte in MACROTEMAS:
                        slug_cidade = restante
                        macrotema = MACROTEMAS[primeira_parte]["nome"]
                    else:
                        slug_cidade, _timestamp = slug_completo.rsplit("__", 1)
            else:
                slug_cidade = slug_completo

            cidade = re.sub(r"_+", " ", slug_cidade).strip().title()

            # compute stable timestamps for both UTC and local timezone
            last_modified_utc = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            last_modified_local = last_modified_utc.astimezone(local_tz)

            relatorios.append({
                "cidade": cidade,
                "macrotema": macrotema,
                "arquivo_pdf": entrada.name,
                "arquivo_html": html_file.name if html_file.exists() else None,
                "arquivo_mapa": mapa_file.name if mapa_file.exists() else None,
                "data": criado_em.strftime("%d/%m/%Y"),
                "hora": criado_em.strftime("%H:%M:%S"),
                "last_modified_utc": last_modified_utc.isoformat(),
                "last_modified_local": last_modified_local.isoformat(),
                # preformatted display fields (local timezone) to avoid client/SSR
                # formatting inconsistencies across deployments
                "display_date": last_modified_local.strftime("%d/%m/%Y"),
                "display_time": last_modified_local.strftime("%H:%M:%S"),
                "pdf_url": f"/output/v{pdf_version}/{entrada.name}",
                "html_url": (
                    f"/output/v{html_version}/{html_file.name}"
                    if html_version is not None else None
                ),
                "mapa_url": (
                    f"/output/v{mapa_version}/{mapa_file.name}"
                    if mapa_version is not None else None
                ),
            })

    # sort by the ISO UTC timestamp so ordering is unambiguous
    relatorios.sort(key=lambda item: item.get("last_modified_utc", ""), reverse=True)

    return relatorios


def _artefatos_do_relatorio(nome_base: str) -> list[Path]:
    sufixo = nome_base.replace("relatorio_", "", 1)
    cidade = sufixo.rsplit("__", 1)[-1]
    artefatos = [
        OUTPUT_DIR / f"{nome_base}.pdf",
        OUTPUT_DIR / f"{nome_base}.html",
        OUTPUT_DIR / f"mapa_regiao_{sufixo}.png",
    ]
    artefatos.extend(sorted(OUTPUT_DIR.glob(f"grafico_*{cidade}.png")))
    return artefatos


def apagar_relatorio_handler(arquivo_pdf: str):
    nome_arquivo = arquivo_pdf.strip()

    if "/" in nome_arquivo or "\\" in nome_arquivo:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido.")

    if not nome_arquivo.startswith("relatorio_") or not nome_arquivo.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Arquivo de relatório inválido.")

    pdf_path = OUTPUT_DIR / nome_arquivo
    nome_base = pdf_path.stem

    removidos = []
    for caminho in _artefatos_do_relatorio(nome_base):
        if caminho.exists() and caminho.is_file():
            caminho.unlink()
            removidos.append(caminho.name)

    if not removidos:
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")

    return {"ok": True, "removidos": removidos}