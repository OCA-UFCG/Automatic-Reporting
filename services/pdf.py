import logging
import re
from pathlib import Path

from weasyprint import HTML

from config import MAPAS_DIR, OUTPUT_DIR

logger = logging.getLogger(__name__)


def _reescrever_srcs(html_content: str) -> str:
    """Ajusta os src das imagens para o WeasyPrint resolver no disco.

    /output/ vira relativo (resolvido contra base_url=OUTPUT_DIR); /mapas/ vira
    file:// absoluto porque a pasta de mapas é irmã do output, fora do base_url.
    """
    html_content = re.sub(r'src="/output/', 'src="', html_content)
    return re.sub(
        r'src="/mapas/',
        f'src="file://{MAPAS_DIR.resolve()}/',
        html_content,
    )


def _gerar_pdf_sync(html_content: str, pdf_file: Path) -> bool:
    try:
        pdf_html = _reescrever_srcs(html_content)
        HTML(string=pdf_html, base_url=str(OUTPUT_DIR.resolve())).write_pdf(str(pdf_file))
    except (OSError, RuntimeError, TypeError, ValueError):
        logger.exception("Falha ao gerar PDF %s", pdf_file)
        return False
    return True


async def _gerar_pdf(html_content: str, pdf_file: Path) -> bool:
    import asyncio
    return await asyncio.to_thread(_gerar_pdf_sync, html_content, pdf_file)
