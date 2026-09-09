"""Setup compartilhado dos gráficos matplotlib.

Roda uma vez no primeiro import de qualquer ``plotting.*``: registra a fonte
Inter (mesma do relatório HTML) e a torna padrão, para os gráficos casarem com
a tipografia do restante do documento. Sem isso o matplotlib cai no DejaVu Sans.
"""

import logging
from pathlib import Path

from matplotlib import font_manager, rcParams

logger = logging.getLogger(__name__)

_FONTS_DIR = Path(__file__).resolve().parent.parent / "report" / "src" / "styles" / "fonts"
_ARQUIVOS_INTER = ("Inter-Regular.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf")


def _registrar_inter() -> None:
    faltando = []
    for nome in _ARQUIVOS_INTER:
        caminho = _FONTS_DIR / nome
        if caminho.exists():
            font_manager.fontManager.addfont(str(caminho))
        else:
            faltando.append(nome)
    if faltando:
        # Sem a fonte, o matplotlib usa o default; o relatório ainda gera.
        logger.warning("Fontes Inter ausentes em %s: %s", _FONTS_DIR, faltando)
        return
    rcParams["font.family"] = "Inter"


_registrar_inter()
