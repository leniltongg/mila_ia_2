import pymysql
from werkzeug.security import generate_password_hash

def create_super_admin():
    # Conectar ao MySQL
    mysql_conn = pymysql.connect(
        host='127.0.0.1',
        user='mila_user',
        password='31952814Gg@',
        database='mila_educacional'
    )
    mysql_cursor = mysql_conn.cursor()

    try:
        # Verificar se o tipo de usuário 6 (Super Admin) existe
        mysql_cursor.execute("SELECT id FROM tipos_usuarios WHERE id = 6")
        tipo_admin = mysql_cursor.fetchone()
        
        if not tipo_admin:
            # Criar tipo de usuário Super Admin
            mysql_cursor.execute(
                "INSERT INTO tipos_usuarios (id, descricao) VALUES (%s, %s)",
                (6, 'Super Administrador')
            )
            mysql_conn.commit()
            print("Tipo de usuário Super Administrador criado com sucesso!")

        # Verificar se o usuário já existe
        mysql_cursor.execute("SELECT id FROM usuarios WHERE email = %s", ('admin@admin.com',))
        admin = mysql_cursor.fetchone()
        
        if not admin:
            # Criar usuário super admin
            mysql_cursor.execute("""
                INSERT INTO usuarios (
                    nome, 
                    email, 
                    senha, 
                    tipo_usuario_id,
                    cidade_id
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                'Super Admin',
                'admin@admin.com',
                generate_password_hash('admin123'),
                6,
                1  # ID da primeira cidade
            ))
            mysql_conn.commit()
            print("Usuário Super Admin criado com sucesso!")
            print("Email: admin@admin.com")
            print("Senha: admin123")
        else:
            print("Usuário Super Admin já existe!")

    except Exception as e:
        print(f"Erro ao criar super admin: {str(e)}")
        mysql_conn.rollback()
    finally:
        mysql_cursor.close()
        mysql_conn.close()

if __name__ == '__main__':
    create_super_admin()
