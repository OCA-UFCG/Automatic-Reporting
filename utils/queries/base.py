import logging

import psycopg2

from utils.database import get_connection

logger = logging.getLogger(__name__)


def escalar_valor(valor: object) -> tuple[object, object]:
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


def executar_query_dict(query: str, params: tuple, contexto_erro: str) -> dict | None:
    """Como `executar_query`, mas mapeia a primeira linha para um dict usando
    os nomes de coluna do cursor (útil para `SELECT *` em views largas)."""
    try:
        conn = get_connection()
    except psycopg2.Error as err:
        logger.warning("Falha ao conectar ao banco de dados: %s", err)
        return None

    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            linha = cursor.fetchone()
            if linha is None:
                return None
            colunas = [descricao[0] for descricao in cursor.description]
            return dict(zip(colunas, linha))
    except psycopg2.Error as err:
        logger.warning("Falha ao executar query (%s): %s", contexto_erro, err)
        return None
    finally:
        conn.close()


def executar_query_dicts(query: str, params: tuple, contexto_erro: str) -> list[dict] | None:
    """Como `executar_query_dict`, mas devolve todas as linhas.

    Existe para as buscas que não sabem a UF de antemão: elas precisam ver
    todas as linhas com aquele nome para detectar cidade ambígua."""
    try:
        conn = get_connection()
    except psycopg2.Error as err:
        logger.warning("Falha ao conectar ao banco de dados: %s", err)
        return None

    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            linhas = cursor.fetchall()
            colunas = [descricao[0] for descricao in cursor.description]
            return [dict(zip(colunas, linha)) for linha in linhas]
    except psycopg2.Error as err:
        logger.warning("Falha ao executar query (%s): %s", contexto_erro, err)
        return None
    finally:
        conn.close()
