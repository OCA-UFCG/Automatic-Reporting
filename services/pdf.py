import logging
import os
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
    # Escrita atômica: renderiza num .tmp e só então os.replace no destino, pra o
    # gate de cache nunca ler um PDF meio-escrito (o handler async cede em cada
    # await, então requests da mesma chave se intercalam mesmo sob 1 worker).
    tmp_file = pdf_file.with_name(pdf_file.name + ".tmp")
    try:
        pdf_html = _reescrever_srcs(html_content)
        HTML(string=pdf_html, base_url=str(OUTPUT_DIR.resolve())).write_pdf(str(tmp_file))
        os.replace(tmp_file, pdf_file)
    except (OSError, RuntimeError, TypeError, ValueError):
        logger.exception("Falha ao gerar PDF %s", pdf_file)
        try:
            tmp_file.unlink()
        except FileNotFoundError:
            pass
        return False
    return True


async def _gerar_pdf(html_content: str, pdf_file: Path) -> bool:
    import asyncio
    return await asyncio.to_thread(_gerar_pdf_sync, html_content, pdf_file)
