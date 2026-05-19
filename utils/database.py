import psycopg2

try:
    conexao = psycopg2.connect(
        host="db.oca-portal.com",
        database="oca_server",
        user="oca-user",
        password="oca2026!",
        port="5432"
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
