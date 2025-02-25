import mysql.connector

# Configuração do banco de dados
config = {
    'user': 'mila_user',
    'password': '31952814Gg@',
    'host': 'localhost',
    'database': 'mila_educacional'
}

# Query para remover registros órfãos
clean_query = """
DELETE d FROM desempenho_simulado d
LEFT JOIN simulados_gerados g ON d.simulado_id = g.id
WHERE g.id IS NULL;
"""

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

try:
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    
    print("Removendo registros órfãos...")
    cursor.execute(clean_query)
    print(f"Registros removidos: {cursor.rowcount}")
    
    print("\nRemovendo chave estrangeira antiga...")
    cursor.execute(drop_fk)
    
    print("Adicionando nova chave estrangeira...")
    cursor.execute(add_fk)
    
    conn.commit()
    print("\nAlterações realizadas com sucesso!")
    
except Exception as e:
    print(f"Erro: {str(e)}")
    conn.rollback()
    
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()
