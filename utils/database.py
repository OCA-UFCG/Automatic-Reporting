import sqlite3

from config import DATABASE_PATH

conn = sqlite3.connect(DATABASE_PATH)
cursor = conn.cursor()

def coleta_id_ibge(cidade: str):
    nm_mun, uf = separa_nome_uf(cidade)

    cursor.execute(f"SELECT id_ibge FROM charts WHERE nm_mun = '{nm_mun}' AND uf = '{uf}';")

    return cursor.fetchone()[0];

def separa_nome_uf(nome: str):
    nm_mun, uf = nome.split(" (")

    return nm_mun, uf.replace(")", "")
