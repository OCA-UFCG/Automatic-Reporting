import logging
import re
from pathlib import Path

from weasyprint import HTML

from config import OUTPUT_DIR

logger = logging.getLogger(__name__)


def _gerar_pdf_sync(html_content: str, pdf_file: Path) -> bool:
    try:
        pdf_html = re.sub(r'src="/output/', 'src="', html_content)
        HTML(string=pdf_html, base_url=str(OUTPUT_DIR.resolve())).write_pdf(str(pdf_file))
    except (OSError, RuntimeError, TypeError, ValueError):
        logger.exception("Falha ao gerar PDF %s", pdf_file)
        return False
    return True


async def _gerar_pdf(html_content: str, pdf_file: Path) -> bool:
    import asyncio
    return await asyncio.to_thread(_gerar_pdf_sync, html_content, pdf_file)
