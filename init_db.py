import sqlite3
import os
from werkzeug.security import generate_password_hash

def init_database():
    """Inicializa o banco de dados com as tabelas necessárias"""
    
    # Verifica se o banco de dados já existe
    if os.path.exists('mila.db'):
        print("Banco de dados já existe. Fazendo backup...")
        if os.path.exists('mila.db.bak'):
            os.remove('mila.db.bak')
        os.rename('mila.db', 'mila.db.bak')
    
    # Conecta ao banco de dados
    conn = sqlite3.connect('mila.db')
    cursor = conn.cursor()
    
    try:
        # Cria tabela de usuários
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                senha_hash TEXT NOT NULL,
                tipo_usuario_id TEXT NOT NULL,
                escola_id INTEGER,
                serie_id INTEGER,
                turma_id INTEGER,
                codigo_ibge TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao_senha TIMESTAMP,
                ultimo_login TIMESTAMP,
                tentativas_login INTEGER DEFAULT 0,
                bloqueado INTEGER DEFAULT 0
            )
        """)
        
        # Cria índices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_tipo ON usuarios(tipo_usuario_id)")
        
        # Cria usuário administrador padrão
        admin_password = "admin123"  # Você deve alterar isso após o primeiro login
        cursor.execute("""
            INSERT INTO usuarios (
                nome, email, senha_hash, tipo_usuario_id
            ) VALUES (?, ?, ?, ?)
        """, (
            "Administrador",
            "admin@mila.com",
            generate_password_hash(admin_password),
            "Administrador"
        ))
        
        # Cria outras tabelas necessárias
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS escolas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                codigo_ibge TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS series (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                escola_id INTEGER,
                FOREIGN KEY (escola_id) REFERENCES escolas (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS turmas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                serie_id INTEGER,
                escola_id INTEGER,
                tipo_ensino TEXT,
                FOREIGN KEY (serie_id) REFERENCES series (id),
                FOREIGN KEY (escola_id) REFERENCES escolas (id)
            )
        """)
        
        conn.commit()
        print("Banco de dados inicializado com sucesso!")
        print("Usuário admin criado:")
        print("Email: admin@mila.com")
        print("Senha: admin123")
        print("IMPORTANTE: Altere a senha do administrador após o primeiro login!")
        
    except Exception as e:
        conn.rollback()
        print(f"Erro ao inicializar o banco de dados: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    init_database()
