import logging
import time

import psycopg2

from utils.database import get_connection

logger = logging.getLogger(__name__)


def executar_query(
    query: str, params: tuple, contexto_erro: str, buscar_todas: bool = False
) -> list | tuple | None:
    t0 = time.perf_counter()
    try:
        conn = get_connection()
    except psycopg2.Error as err:
        logger.warning("Falha ao conectar ao banco de dados: %s", err)
        return None
    t_connect = time.perf_counter()

    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            resultado = cursor.fetchall() if buscar_todas else cursor.fetchone()
        t_query = time.perf_counter()
        logger.info(
            "[timing][db] %s: connect=%.3fs query=%.3fs total=%.3fs",
            contexto_erro, t_connect - t0, t_query - t_connect, t_query - t0,
        )
        return resultado
    except psycopg2.Error as err:
        logger.warning("Falha ao executar query (%s): %s", contexto_erro, err)
        return None
    finally:
        conn.close()
