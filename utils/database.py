import psycopg2

from config import (
    DB_DATABASE,
    DB_HOST,
    DB_PASSWORD,
    DB_PORT,
    DB_STATEMENT_TIMEOUT_MS,
    DB_USER,
)


def get_connection():
    # Guard do CLAUDE.md: vw_perfil_* nunca deveriam rodar sem statement_timeout —
    # vw_perfil_economia mede >30s em produção e, sem esse cap, a query pendura o
    # worker único do uvicorn indefinidamente. Com o timeout, a query aborta e
    # executar_query (utils/queries/base.py) já trata psycopg2.Error como "sem
    # dados", caindo no fallback CSV / placeholder vazio.
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_DATABASE,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        connect_timeout=5,
        options=f"-c statement_timeout={DB_STATEMENT_TIMEOUT_MS}",
    )


def test_connection():
    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()

        print("Conexão bem-sucedida!")
        print(f"Versão do banco de dados: {version[0]}")
        return {"status": "connected", "version": version[0]}
    except psycopg2.Error as e:
        print(f"Erro na conexão com o banco de dados: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        if conn is not None:
            conn.close()


def main():
    test_connection()

if __name__ == "__main__":
    main()
