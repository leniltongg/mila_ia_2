import mysql.connector

# Configuração do banco de dados
config = {
    'user': 'mila_user',
    'password': '31952814Gg@',
    'host': 'localhost',
    'database': 'mila_educacional'
}

# Query para verificar registros órfãos
check_query = """
SELECT d.simulado_id, COUNT(*) as count
FROM desempenho_simulado d
LEFT JOIN simulados_gerados g ON d.simulado_id = g.id
WHERE g.id IS NULL
GROUP BY d.simulado_id;
"""

try:
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    
    print("Verificando registros órfãos em desempenho_simulado...")
    cursor.execute(check_query)
    results = cursor.fetchall()
    
    if results:
        print("\nEncontrados registros sem correspondência em simulados_gerados:")
        for simulado_id, count in results:
            print(f"simulado_id: {simulado_id}, quantidade: {count}")
    else:
        print("\nNenhum registro órfão encontrado!")
    
except Exception as e:
    print(f"Erro: {str(e)}")
    
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()
