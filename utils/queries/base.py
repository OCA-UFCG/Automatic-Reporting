import logging

import psycopg2

from utils.database import get_connection

logger = logging.getLogger(__name__)


def executar_query(
    query: str, params: tuple, contexto_erro: str, buscar_todas: bool = False
) -> list | tuple | None:
    try:
        conn = get_connection()
    except psycopg2.Error as err:
        logger.warning("Falha ao conectar ao banco de dados: %s", err)
        return None

    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall() if buscar_todas else cursor.fetchone()
    except psycopg2.Error as err:
        logger.warning("Falha ao executar query (%s): %s", contexto_erro, err)
        return None
    finally:
        conn.close()
