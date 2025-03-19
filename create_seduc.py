import pymysql
from werkzeug.security import generate_password_hash

def create_seduc():
    # Conectar ao MySQL
    mysql_conn = pymysql.connect(
        host='127.0.0.1',
        user='mila_user',
        password='31952814Gg@',
        database='mila_educacional'
    )
    mysql_cursor = mysql_conn.cursor()

    try:
        # Verificar se o usuário já existe
        mysql_cursor.execute("SELECT id FROM usuarios WHERE email = %s", ('seduc@email.com',))
        seduc = mysql_cursor.fetchone()
        
        if not seduc:
            # Primeiro, vamos obter o ID da cidade pelo código IBGE
            mysql_cursor.execute("SELECT id FROM cidades WHERE codigo_ibge = %s", (2910800,))
            cidade = mysql_cursor.fetchone()
            
            if not cidade:
                print("Erro: Cidade com código IBGE 2910800 não encontrada!")
                return
                
            cidade_id = cidade[0]
            
            # Criar usuário da secretaria de educação
            mysql_cursor.execute("""
                INSERT INTO usuarios (
                    nome, 
                    email, 
                    senha, 
                    tipo_usuario_id,
                    cidade_id,
                    codigo_ibge
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                'seduc',
                'seduc@email.com',
                generate_password_hash('123456'),
                5,  # tipo_usuario_id = 5 (Secretaria de Educação)
                cidade_id,
                '2910800'
            ))
            mysql_conn.commit()
            print("Usuário da Secretaria de Educação criado com sucesso!")
            print("Email: seduc@email.com")
            print("Senha: 123456")
        else:
            print("Usuário da Secretaria de Educação já existe!")

    except Exception as e:
        print(f"Erro ao criar usuário da Secretaria de Educação: {str(e)}")
        mysql_conn.rollback()
    finally:
        mysql_cursor.close()
        mysql_conn.close()

if __name__ == '__main__':
    create_seduc()
