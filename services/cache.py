"""Cache em disco de relatórios prontos: frescor e limite de tamanho.

Frescor = "gerado depois da última mudança de dado". A mudança é sinalizada
por output/.data_version, tocado pelo refresh noturno das materialized views.
Se o marcador não existe, nada foi invalidado ainda -> tudo é fresco.
"""

from __future__ import annotations

from pathlib import Path

from config import OUTPUT_DIR

DATA_VERSION_FILE = OUTPUT_DIR / ".data_version"


def _data_version_mtime() -> float:
    try:
        return DATA_VERSION_FILE.stat().st_mtime
    except FileNotFoundError:
        return 0.0  # sem marcador = dado nunca invalidado


def artefato_fresco(caminho: Path) -> bool:
    """True se o arquivo existe e foi gerado depois da última mudança de dado."""
    try:
        return caminho.stat().st_mtime > _data_version_mtime()
    except FileNotFoundError:
        return False
