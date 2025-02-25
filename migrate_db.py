import sqlite3
from werkzeug.security import generate_password_hash
import os
from datetime import datetime

def migrate_database():
    """Migra o banco de dados antigo para o novo formato com senhas hasheadas"""
    
    # Backup do banco de dados antigo
    if os.path.exists('mila.db'):
        backup_name = f'mila_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        print(f"Criando backup do banco de dados: {backup_name}")
        with open('mila.db', 'rb') as src, open(backup_name, 'wb') as dst:
            dst.write(src.read())

    # Conecta ao banco de dados
    conn = sqlite3.connect('mila.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Verifica se a coluna senha_hash já existe
        cursor.execute("PRAGMA table_info(usuarios)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Adiciona novas colunas se não existirem
        new_columns = {
            'senha_hash': 'TEXT',
            'data_criacao': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'data_atualizacao_senha': 'TIMESTAMP',
            'ultimo_login': 'TIMESTAMP',
            'tentativas_login': 'INTEGER DEFAULT 0',
            'bloqueado': 'INTEGER DEFAULT 0'
        }

        for column, type_ in new_columns.items():
            if column not in columns:
                print(f"Adicionando coluna {column}")
                cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {column} {type_}")

        # Migra senhas para formato hash se necessário
        if 'senha' in columns and 'senha_hash' in columns:
            print("Migrando senhas para formato hash...")
            cursor.execute("SELECT id, senha FROM usuarios WHERE senha_hash IS NULL")
            users = cursor.fetchall()
            
            for user in users:
                if user['senha']:  # Verifica se a senha não é None
                    senha_hash = generate_password_hash(user['senha'])
                    cursor.execute("""
                        UPDATE usuarios 
                        SET senha_hash = ?,
                            data_atualizacao_senha = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (senha_hash, user['id']))

            # Remove a coluna antiga de senha
            print("Removendo coluna antiga de senha...")
            cursor.execute("""
                CREATE TABLE usuarios_new AS 
                SELECT id, nome, email, senha_hash, tipo_usuario_id, escola_id, 
                       Ano_escolar_id, turma_id, codigo_ibge, data_criacao, 
                       data_atualizacao_senha, ultimo_login, tentativas_login, bloqueado
                FROM usuarios
            """)
            cursor.execute("DROP TABLE usuarios")
            cursor.execute("ALTER TABLE usuarios_new RENAME TO usuarios")

        # Cria índices
        print("Criando índices...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_tipo ON usuarios(tipo_usuario_id)")

        conn.commit()
        print("Migração concluída com sucesso!")

    except Exception as e:
        conn.rollback()
        print(f"Erro durante a migração: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database()
