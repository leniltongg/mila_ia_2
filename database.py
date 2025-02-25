import sqlite3
from flask import g
from flask_sqlalchemy import SQLAlchemy
import logging
import click
from contextlib import contextmanager

# Caminho do banco de dados que você quer usar
DB_PATH = 'educacional.db'  # Altere para o nome correto do seu banco

db = SQLAlchemy()

def get_db():
    if 'db' not in g:
        g.db = db
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.session.close()

@contextmanager
def get_db_cursor():
    """Contexto seguro para operações com o banco de dados"""
    db = get_db()
    cursor = db.session
    try:
        yield cursor
        cursor.commit()
    except Exception as e:
        cursor.rollback()
        logging.error(f"Erro na operação do banco de dados: {str(e)}")
        raise
    finally:
        cursor.close()

def init_db():
    """Inicializa o banco de dados com as tabelas necessárias"""
    db = get_db()
    db.create_all()

    # Tabela de usuários
    db.session.execute("""
        CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email)
    """)
    db.session.execute("""
        CREATE INDEX IF NOT EXISTS idx_usuarios_tipo ON usuarios(tipo_usuario_id)
    """)
    db.session.execute("""
        CREATE INDEX IF NOT EXISTS idx_usuarios_escola ON usuarios(escola_id)
    """)
    db.session.execute("""
        CREATE INDEX IF NOT EXISTS idx_usuarios_codigo_ibge ON usuarios(codigo_ibge)
    """)

    # Tabela de log de atividades
    db.session.execute("""
        CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_log(user_id)
    """)
    db.session.execute("""
        CREATE INDEX IF NOT EXISTS idx_activity_type ON activity_log(activity_type)
    """)
    db.session.execute("""
        CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_log(timestamp)
    """)

    # Commit das alterações
    db.session.commit()

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
