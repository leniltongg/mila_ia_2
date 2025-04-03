import pymysql

# Configuração do banco de dados
DB_USER = 'mila_user'
DB_PASSWORD = '31952814Gg@'
DB_HOST = '127.0.0.1'
DB_NAME = 'mila_educacional'

# SQL para adicionar a coluna
sql = """
ALTER TABLE temas_redacao
ADD COLUMN ativo BOOLEAN DEFAULT TRUE;
"""

try:
    # Conectar ao banco
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    
    # Criar cursor e executar o SQL
    with conn.cursor() as cursor:
        cursor.execute(sql)
        conn.commit()
        print("Coluna 'ativo' adicionada com sucesso à tabela temas_redacao!")
except Exception as e:
    print(f"Erro ao adicionar coluna: {str(e)}")
finally:
    if 'conn' in locals():
        conn.close()
