import mysql.connector

# Configuração do banco de dados
config = {
    'user': 'mila_user',
    'password': '31952814Gg@',
    'host': 'localhost',
    'database': 'mila_educacional'
}

# Remover a chave estrangeira antiga
drop_fk = """
ALTER TABLE desempenho_simulado 
DROP FOREIGN KEY desempenho_simulado_ibfk_4;
"""

# Adicionar a nova chave estrangeira para simulados_gerados
add_fk = """
ALTER TABLE desempenho_simulado
ADD CONSTRAINT desempenho_simulado_ibfk_4
FOREIGN KEY (simulado_id) REFERENCES simulados_gerados(id);
"""

# Executar as alterações
try:
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    
    print("Removendo chave estrangeira antiga...")
    cursor.execute(drop_fk)
    
    print("Adicionando nova chave estrangeira...")
    cursor.execute(add_fk)
    
    conn.commit()
    print("Alterações realizadas com sucesso!")
    
except Exception as e:
    print(f"Erro: {str(e)}")
    
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()
