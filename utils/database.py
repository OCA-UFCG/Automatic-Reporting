import psycopg2
from config import DB_HOST
from config import DB_DATABASE
from config import DB_USER
from config import DB_PASSWORD
from config import DB_PORT

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
    except Exception as e:
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
    except Exception as e:
        return {"status": "error", "message": str(e)}

def main():
    test_connection()

if __name__ == "__main__":
    main()
