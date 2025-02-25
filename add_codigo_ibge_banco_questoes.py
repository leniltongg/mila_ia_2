import mysql.connector
from mysql.connector import Error

def add_codigo_ibge_to_banco_questoes():
    connection = None
    try:
        connection = mysql.connector.connect(
            host='127.0.0.1',
            database='mila_educacional',
            user='mila_user',
            password='31952814Gg@'
        )

        if connection.is_connected():
            cursor = connection.cursor()

            # 1. Adicionar a coluna codigo_ibge
            try:
                cursor.execute('ALTER TABLE banco_questoes ADD COLUMN codigo_ibge VARCHAR(7)')
                connection.commit()
                print("Coluna codigo_ibge adicionada com sucesso")
            except Error as e:
                print(f"Erro ao adicionar coluna (pode ser que já exista): {str(e)}")
                connection.rollback()

            # 2. Pegar o codigo_ibge do usuário seduc
            cursor.execute("SELECT codigo_ibge FROM usuarios WHERE email = 'seduc@email.com'")
            result = cursor.fetchone()
            
            if not result:
                print("Usuário seduc não encontrado!")
                return
            
            codigo_ibge = result[0]
            if not codigo_ibge:
                print("Usuário seduc não tem codigo_ibge!")
                return

            # 3. Atualizar todas as questões com o codigo_ibge do seduc
            try:
                cursor.execute(
                    'UPDATE banco_questoes SET codigo_ibge = %s',
                    (codigo_ibge,)
                )
                connection.commit()
                print(f"Registros atualizados com codigo_ibge: {codigo_ibge}")
            except Error as e:
                print(f"Erro ao atualizar registros: {str(e)}")
                connection.rollback()

    except Error as e:
        print(f"Erro ao conectar ao MySQL: {str(e)}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print("Conexão com MySQL fechada")

if __name__ == '__main__':
    add_codigo_ibge_to_banco_questoes()
