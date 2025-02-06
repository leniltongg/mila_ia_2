import sqlite3
from flask import g
from contextlib import contextmanager
import logging
import click

# Caminho do banco de dados que você quer usar
DB_PATH = 'educacional.db'  # 🔹 Altere para o nome correto do seu banco

def get_db():
    """Obtém a conexão com o banco de dados"""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row  # Retorna os resultados como dicionários
    
    return g.db

def close_db(e=None):
    """Fecha a conexão com o banco de dados"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

@contextmanager
def get_db_cursor():
    """Contexto seguro para operações com o banco de dados"""
    db = get_db()
    cursor = db.cursor()
    try:
        yield cursor
        db.commit()
    except Exception as e:
        db.rollback()
        logging.error(f"Erro na operação do banco de dados: {str(e)}")
        raise
    finally:
        cursor.close()

def init_db():
    """Inicializa o banco de dados com as tabelas necessárias"""
    db = get_db()
    cursor = db.cursor()

    # Tabela de usuários
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
            bloqueado INTEGER DEFAULT 0,
            FOREIGN KEY (escola_id) REFERENCES escolas (id),
            FOREIGN KEY (serie_id) REFERENCES series (id),
            FOREIGN KEY (turma_id) REFERENCES turmas (id)
        )
    """)

    # Índices para performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_tipo ON usuarios(tipo_usuario_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_escola ON usuarios(escola_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_codigo_ibge ON usuarios(codigo_ibge)")

    # Tabela de log de atividades
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            activity_type TEXT,
            details TEXT,
            ip_address TEXT,
            user_agent TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES usuarios (id)
        )
    """)

    # Índices para o log
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_log(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_type ON activity_log(activity_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_log(timestamp)")

    # Commit das alterações
    db.commit()

@click.command('init-db')
def init_db_command():
    """Limpa os dados existentes e recria as tabelas"""
    init_db()
    click.echo('Banco de dados inicializado.')

def update_user_login(user_id):
    """Atualiza a data do último login do usuário"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            UPDATE usuarios 
            SET ultimo_login = CURRENT_TIMESTAMP,
                tentativas_login = 0
            WHERE id = ?
        """, (user_id,))

def increment_login_attempts(email):
    """Incrementa o contador de tentativas de login"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            UPDATE usuarios 
            SET tentativas_login = tentativas_login + 1
            WHERE email = ?
        """, (email,))

def reset_login_attempts(email):
    """Reseta o contador de tentativas de login"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            UPDATE usuarios 
            SET tentativas_login = 0
            WHERE email = ?
        """, (email,))
