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


def buscar_perfil_municipal(
    view: str, nome_municipio: str, sigla_uf: str, contexto_erro: str
) -> dict[str, object] | None:
    """Busca a linha de uma view `relatorios_auto.vw_perfil_*` de um município.

    `view` nunca vem de entrada do usuário, sempre um literal do código chamador.
    """
    try:
        conn = get_connection()
    except psycopg2.Error as err:
        logger.warning("Falha ao conectar ao banco de dados: %s", err)
        return None

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM {view} WHERE nm_mun = %s AND sigla_uf = %s",
                (nome_municipio, sigla_uf),
            )
            linha = cursor.fetchone()
            if linha is None:
                return None
            colunas = [coluna.name for coluna in cursor.description]
    except psycopg2.Error as err:
        logger.warning("Falha ao executar query (%s): %s", contexto_erro, err)
        return None
    finally:
        conn.close()

    return {campo: valor for campo, valor in zip(colunas, linha) if valor is not None}
