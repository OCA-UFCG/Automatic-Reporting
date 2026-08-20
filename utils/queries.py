import logging

import psycopg2

from utils.database import get_connection

logger = logging.getLogger(__name__)

MESES_PT = {
    1: "janeiro",
    2: "fevereiro",
    3: "março",
    4: "abril",
    5: "maio",
    6: "junho",
    7: "julho",
    8: "agosto",
    9: "setembro",
    10: "outubro",
    11: "novembro",
    12: "dezembro",
}

CARACTERISTICAS_MUNICIPIO = """
    SELECT
        c.nm_mun,
        c.sigla_uf,
        c.estado,
        c.regiao,
        c.nm_rgi,
        c.area,
        c.bioma,
        n.dia,
        n.mes
    FROM carac_mun.caracteristicas_municipais c
    LEFT JOIN carac_mun.niver_municipais n
        ON (c.cd_mun::int / 10) = n.codigo_municipio::int
    WHERE c.nm_mun = %s
      AND c.sigla_uf = %s
"""


def buscar_caracteristicas_municipio(
    nome_municipio: str, sigla_uf: str
) -> dict[str, object] | None:
    try:
        conn = get_connection()
    except psycopg2.Error as err:
        logger.warning("Falha ao conectar ao banco de dados: %s", err)
        return None

    try:
        with conn.cursor() as cursor:
            cursor.execute(CARACTERISTICAS_MUNICIPIO, (nome_municipio, sigla_uf))
            linha = cursor.fetchone()
    except psycopg2.Error as err:
        logger.warning(
            "Falha ao buscar características do município '%s (%s)': %s",
            nome_municipio,
            sigla_uf,
            err,
        )
        return None
    finally:
        conn.close()

    if linha is None:
        return None

    nm_mun, sigla_uf_db, estado, regiao, nm_rgi, area, bioma, dia, mes = linha

    aniversario = None
    if dia is not None and mes is not None and mes in MESES_PT:
        aniversario = f"{dia} de {MESES_PT[mes]}"

    dados = {
        "nm_mun": nm_mun,
        "sigla_uf": sigla_uf_db,
        "estado": estado,
        "regiao": regiao,
        "nm_rgi": nm_rgi,
        "area": area,
        "bioma": bioma,
        "aniversario": aniversario,
    }
    return {campo: valor for campo, valor in dados.items() if valor is not None}
