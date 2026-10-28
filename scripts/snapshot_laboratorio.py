#!/usr/bin/env python3
"""Gera o snapshot do Laboratório de Temas (output/laboratorio/<tema>.json.gz).

Só o gamma roda isto (o laboratório só existe lá). Rodada completa toda noite, encadeada
no ~/scripts/refresh_matviews.sh do gamma depois do touch .data_version, e à mão depois
de uma carga de dados de um tema:

    docker exec automatic-reporting-gamma flock -n /app/output/laboratorio.lock \\
        python3 scripts/snapshot_laboratorio.py [--tema saneamento]

O flock impede a rodada manual e a noturna de rodarem juntas: um tema por vez, nunca em
paralelo, é parte da exceção ao guard do SELECT * (ver services/laboratorio_snapshot.py).
Os 8 temas levaram ~24 min no gamma (medição de 26/10/2026).

Sai com código 1 se algum tema abortou (o arquivo anterior dele fica), pro cron registrar.
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Antes de qualquer conexão: identifica o job no pg_stat_activity.
os.environ.setdefault("PGAPPNAME", "laboratorio-snapshot")

from services.laboratorio_snapshot import gerar_snapshot_tema
from utils.queries.perfil_municipal import VIEW_POR_MACROTEMA

logger = logging.getLogger("snapshot_laboratorio")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tema", choices=sorted(VIEW_POR_MACROTEMA))
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)sZ %(levelname)s %(name)s: %(message)s"
    )
    logging.Formatter.converter = time.gmtime  # a VM roda em UTC; o log também

    temas = [args.tema] if args.tema else list(VIEW_POR_MACROTEMA)
    abortados = []
    for slug in temas:
        try:
            gravado = gerar_snapshot_tema(slug)
        except Exception:
            logger.exception("snapshot %s: erro inesperado; mantém o anterior", slug)
            gravado = None
        if gravado is None:
            abortados.append(slug)

    if abortados:
        logger.error("temas que mantiveram o snapshot anterior: %s", ", ".join(abortados))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
