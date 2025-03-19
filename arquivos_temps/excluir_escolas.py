import mysql.connector
from datetime import datetime

def get_connection():
    return mysql.connector.connect(
        host='127.0.0.1',
        database='mila_educacional',
        user='mila_user',
        password='31952814Gg@'
    )

def excluir_escolas(id_inicial, id_final, confirmar=False):
    """
    Exclui escolas dentro do intervalo especificado.
    
    Args:
        id_inicial (int): ID inicial do intervalo de escolas a serem excluídas
        id_final (int): ID final do intervalo de escolas a serem excluídas
        confirmar (bool): Se True, executa a exclusão. Se False, apenas mostra o que seria excluído
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Primeiro, vamos ver quais escolas seriam excluídas
        cursor.execute("""
            SELECT id, nome, municipio_id 
            FROM escolas 
            WHERE id BETWEEN %s AND %s
            ORDER BY id
        """, (id_inicial, id_final))
        
        escolas = cursor.fetchall()
        
        print(f"\nEscolas que serão excluídas ({len(escolas)} escolas):")
        print("-" * 50)
        for id_escola, nome, municipio_id in escolas:
            print(f"ID: {id_escola}, Nome: {nome}, Município ID: {municipio_id}")
        
        if not confirmar:
            print("\nEste foi apenas um teste. Para excluir as escolas, execute novamente com confirmar=True")
            return
        
        # Se confirmado, exclui as escolas
        cursor.execute("""
            DELETE FROM escolas 
            WHERE id BETWEEN %s AND %s
        """, (id_inicial, id_final))
        
        conn.commit()
        print(f"\nExclusão concluída! {cursor.rowcount} escolas foram excluídas.")

    except Exception as e:
        print(f"Erro ao excluir escolas: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    # Primeiro rode com confirmar=False para ver quais escolas serão excluídas
    # excluir_escolas(1, 100, confirmar=False)
    
    # Depois, se as escolas estiverem corretas, rode com confirmar=True
    excluir_escolas(1, 5012, confirmar=True)
