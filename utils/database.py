import psycopg2

from config import DB_DATABASE, DB_HOST, DB_PASSWORD, DB_PORT, DB_USER


def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_DATABASE,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        connect_timeout=5,
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
