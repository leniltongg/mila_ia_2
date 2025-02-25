import mysql.connector

config = {
    'user': 'mila_user',
    'password': '31952814Gg@',
    'host': 'localhost',
    'database': 'mila_educacional'
}

# Remover a chave estrangeira de simulados_enviados
drop_fk = """
ALTER TABLE simulados_enviados 
DROP FOREIGN KEY simulados_enviados_ibfk_1;
"""

try:
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    
    print("Removendo chave estrangeira...")
    cursor.execute(drop_fk)
    
    conn.commit()
    print("Alterações realizadas com sucesso!")
    
except Exception as e:
    print(f"Erro: {str(e)}")
    
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()
