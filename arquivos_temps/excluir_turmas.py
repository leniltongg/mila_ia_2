import mysql.connector
from datetime import datetime

def get_connection():
    return mysql.connector.connect(
        host='127.0.0.1',
        database='mila_educacional',
        user='mila_user',
        password='31952814Gg@'
    )

def excluir_turmas(id_inicial, id_final, confirmar=False):
    """
    Exclui turmas dentro do intervalo especificado.
    
    Args:
        id_inicial (int): ID inicial do intervalo de turmas a serem excluídas
        id_final (int): ID final do intervalo de turmas a serem excluídas
        confirmar (bool): Se True, executa a exclusão. Se False, apenas mostra o que seria excluído
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Primeiro, vamos ver quais turmas seriam excluídas
        cursor.execute("""
            SELECT id, turma, escola_id 
            FROM turmas 
            WHERE id BETWEEN %s AND %s
            ORDER BY id
        """, (id_inicial, id_final))
        
        turmas = cursor.fetchall()
        
        print(f"\nTurmas que serão excluídas ({len(turmas)} turmas):")
        print("-" * 50)
        for id_turma, turma, escola_id in turmas:
            print(f"ID: {id_turma}, Turma: {turma}, Escola ID: {escola_id}")
        
        if not confirmar:
            print("\nEste foi apenas um teste. Para excluir as turmas, execute novamente com confirmar=True")
            return
        
        # Primeiro, excluir registros relacionados em simulados_enviados
        print("\nExcluindo registros relacionados...")
        cursor.execute("""
            DELETE FROM simulados_enviados 
            WHERE turma_id BETWEEN %s AND %s
        """, (id_inicial, id_final))
        print(f"- {cursor.rowcount} registros excluídos da tabela simulados_enviados")

        # Excluir registros relacionados em outras tabelas que possam ter foreign key
        # Adicione mais comandos DELETE conforme necessário

        # Por fim, exclui as turmas
        cursor.execute("""
            DELETE FROM turmas 
            WHERE id BETWEEN %s AND %s
        """, (id_inicial, id_final))
        
        conn.commit()
        print(f"\nExclusão concluída! {cursor.rowcount} turmas foram excluídas.")

    except Exception as e:
        print(f"Erro ao excluir turmas: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    # Primeiro rode com confirmar=False para ver quais turmas serão excluídas
    # excluir_turmas(1, 100, confirmar=False)
    
    # Depois, se as turmas estiverem corretas, rode com confirmar=True
    excluir_turmas(1, 5012, confirmar=True)
