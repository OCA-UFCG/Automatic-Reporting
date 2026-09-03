import logging

import psycopg2

from utils.database import get_connection

logger = logging.getLogger(__name__)


def escalar_valor(valor: object) -> tuple[object, object]:
    """Reduz um valor monetário/numérico grande para a menor unidade legível.

    Usado pelos textos dos macrotemas, que esperam o par (valor, unidade) —
    ex.: 12_945_093_200 -> (12.95, "bilhões") — para compor frases como
    "R$ $valor $unidade".
    """
    if valor is None:
        return None, None
    valor = float(valor)
    if valor >= 1_000_000_000:
        return valor / 1_000_000_000, "bilhões"
    if valor >= 1_000_000:
        return valor / 1_000_000, "milhões"
    if valor >= 1_000:
        return valor / 1_000, "mil"
    return valor, ""


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
