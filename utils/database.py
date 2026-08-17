import psycopg2

from config import DB_DATABASE, DB_HOST, DB_PASSWORD, DB_PORT, DB_USER


def get_connection():
    try:
        conexao = psycopg2.connect(
            host= DB_HOST,
            database=DB_DATABASE,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            connect_timeout=5
        )
        
        cursor = conexao.cursor()
        cursor.execute("SELECT version();")
        versao_db = cursor.fetchone()
        print("Conexão bem-sucedida!")
        print(f"Versão do banco de dados: {versao_db[0]}")
        
        cursor.close()
        conexao.close()
        
    except psycopg2.OperationalError as e:
        print(f"Ocorreu um erro operacional (provavelmente rede ou credenciais): {e}")
    except psycopg2.Error as e:
        print(f"Erro: {e}")

def test_connection():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        cursor.close()
        conn.close()
        return {"status": "connected", "version": version[0]}
    except psycopg2.Error as e:
        return {"status": "error", "message": str(e)}

def main():
    test_connection()

if __name__ == "__main__":
    main()
