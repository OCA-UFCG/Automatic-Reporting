"""Relatório de estado e de área com texto, dados e gráficos congelados (beta, 16/11/2026).

Pedido de 16/11/2026: o beta mostra os recortes de estado e de área com textos estáticos,
um por unidade e tema, escritos a partir de um congelamento do gamma. O beta não tem as
matviews `est_*` nem `areaint_*`, então nada aqui consulta o banco. Decisões e o porquê
no Documentacao-OCA (data-nordeste/automatic-reporting/textos-estaticos/DECISOES.md).

Liga com RELATORIO_CONGELADO_DIR (só o cd-beta define). A pasta tem:

    textos/<estado|area>/<tema>/<unidade>.txt      texto do tema, no formato do Doc
    congelado/<estado|area>/<tema>/<unidade>.json  {"linha": {...}} da matview do tema
    congelado/area/geral/<unidade>.json            linha da areaint_geral (DS de área)
    congelado/estado/caract-mun/<unidade>.json     linha da est_caract_mun (1ª página)
    graficos/<estado|area>/<tema>/<unidade>/<marcador>.png

`<unidade>` é o nome sem acento, em minúsculas, com hífens (nome_de_arquivo). Arquivo que
falta faz o tema sumir do relatório, como um tema sem Doc no relatório de hoje.
"""

import json
import logging
import os
import re
import shutil
import unicodedata
from decimal import Decimal
from pathlib import Path

import config
from utils.queries.area import AREAS_DO_TEMA_DE_TEXTO_FIXO

logger = logging.getLogger(__name__)

# Temas que, numa unidade, não têm matview e leem outra pasta de linhas. Espelha
# AREAS_DO_TEMA_DE_TEXTO_FIXO (utils/queries/area.py): DS de área lê a areaint_geral.
_PASTA_DA_LINHA: dict[tuple[str, str], str] = {("area", "desenvolvimento-social"): "geral"}

# Só as colunas `numeric` do banco foram gravadas como texto ("56467.243", "3974687"):
# inteiros e textos de verdade vieram como int e str no JSON. Por isso o texto numérico
# volta a Decimal, como o psycopg2 entregaria, e não a int.
_NUMERICO = re.compile(r"^-?\d+(\.\d+)?$")


def ativo() -> bool:
    """Se o relatório de estado e de área lê a pasta congelada em vez do banco e dos Docs."""
    return bool(config.RELATORIO_CONGELADO_DIR)


def nome_de_arquivo(nome: str) -> str:
    """Ex.: nome_de_arquivo("Área de atuação da Sudene") == "area-de-atuacao-da-sudene" """
    ascii_ = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_).strip("-")


def _pasta() -> Path:
    return Path(config.RELATORIO_CONGELADO_DIR)


def _tipar(valor: object) -> object:
    """Texto numérico do congelamento volta a Decimal, para os placeholders formatarem
    como com o banco (milhar e casas decimais).

    Ex.: _tipar("3974687") == Decimal(3974687); _tipar(2025) == 2025; _tipar("PB") == "PB"
    """
    if isinstance(valor, str) and _NUMERICO.match(valor):
        return Decimal(valor)
    return valor


def _ler_linha(caminho: Path) -> dict | None:
    """A linha do JSON congelado, ou None se não há arquivo. Arquivo ilegível também dá
    None, com aviso: o tema some, como quando o banco falha (executar_query_dict)."""
    if not caminho.is_file():
        return None
    try:
        linha = json.loads(caminho.read_text(encoding="utf-8"))["linha"]
    except (ValueError, KeyError, TypeError) as err:
        logger.warning("Linha congelada ilegível em %s: %r", caminho, err)
        return None
    return {coluna: _tipar(valor) for coluna, valor in linha.items()}


def texto_do_tema(unidade: str, slug: str, nome: str) -> str | None:
    """O texto estático do tema na unidade, ou None se não há arquivo."""
    caminho = _pasta() / "textos" / unidade / slug / f"{nome_de_arquivo(nome)}.txt"
    return caminho.read_text(encoding="utf-8") if caminho.is_file() else None


def linha_do_tema(unidade: str, slug: str, nome: str) -> dict | None:
    """A linha congelada da matview do tema, ou da areaint_geral no DS de área, que vale
    só nas áreas de AREAS_DO_TEMA_DE_TEXTO_FIXO (nas outras o tema some, como hoje)."""
    if (unidade, slug) == ("area", "desenvolvimento-social") and nome not in AREAS_DO_TEMA_DE_TEXTO_FIXO[slug]:
        return None
    pasta = _PASTA_DA_LINHA.get((unidade, slug), slug)
    return _ler_linha(_pasta() / "congelado" / unidade / pasta / f"{nome_de_arquivo(nome)}.json")


def caracteristicas_do_estado(nome: str) -> dict | None:
    """A linha congelada da est_caract_mun, para a primeira página do estado."""
    return _ler_linha(_pasta() / "congelado" / "estado" / "caract-mun" / f"{nome_de_arquivo(nome)}.json")


def graficos_do_tema(unidade: str, slug: str, nome: str, output_dir: Path, sufixo: str) -> dict[str, str]:
    """{marcador: PNG} dos gráficos prontos do tema na unidade, copiados para output_dir
    com o mesmo nome que a geração daria (`<marcador>_<sufixo>.png`). Gráfico sem PNG
    fica de fora e some do relatório junto com a menção "(Figura X)", como hoje."""
    pasta = _pasta() / "graficos" / unidade / slug / nome_de_arquivo(nome)
    if not pasta.is_dir():
        return {}
    output_dir.mkdir(parents=True, exist_ok=True)
    graficos: dict[str, str] = {}
    for png in sorted(pasta.glob("*.png")):
        destino = f"{png.stem}_{sufixo}.png"
        # Cópia para um temporário e troca atômica: uma geração simultânea da mesma
        # unidade nunca lê o PNG pela metade.
        temporario = output_dir / f".{destino}.{os.getpid()}.tmp"
        shutil.copyfile(png, temporario)
        os.replace(temporario, output_dir / destino)
        graficos[png.stem] = destino
    return graficos
