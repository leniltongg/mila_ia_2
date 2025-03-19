import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host='127.0.0.1',
        database='mila_educacional',
        user='mila_user',
        password='31952814Gg@'
    )

def limpar_tabela(nome_tabela, confirmar=False):
    """
    Limpa todos os registros de uma tabela.
    
    Args:
        nome_tabela (str): Nome da tabela a ser limpa
        confirmar (bool): Se True, executa a limpeza. Se False, apenas mostra informações da tabela
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Primeiro, vamos ver quantos registros a tabela tem
        cursor.execute(f"SELECT COUNT(*) FROM {nome_tabela}")
        total_registros = cursor.fetchone()[0]
        
        print(f"\nInformações da tabela {nome_tabela}:")
        print("-" * 50)
        print(f"Total de registros: {total_registros}")
        
        if not confirmar:
            print("\nEste foi apenas um teste. Para limpar a tabela, execute novamente com confirmar=True")
            return
        
        # Se confirmado, limpa a tabela usando TRUNCATE (mais rápido que DELETE)
        cursor.execute(f"TRUNCATE TABLE {nome_tabela}")
        
        conn.commit()
        print(f"\nLimpeza concluída! Todos os {total_registros} registros foram removidos da tabela {nome_tabela}.")

    except Exception as e:
        print(f"Erro ao limpar tabela: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    # Primeiro rode com confirmar=False para ver quantos registros serão excluídos
    # limpar_tabela('nome_da_tabela', confirmar=False)
    
    # Depois, se estiver tudo certo, rode com confirmar=True
    # limpar_tabela('nome_da_tabela', confirmar=True)
    
    # Exemplo para limpar a tabela de turmas:
    # limpar_tabela('turmas', confirmar=True)
