from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import *
import sqlite3
import os

app = Flask(__name__)
app.config.from_object('config.Config')
db.init_app(app)

def create_sqlalchemy_tables():
    with app.app_context():
        print("Criando tabelas do SQLAlchemy...")
        db.create_all()
        print("Tabelas do SQLAlchemy criadas com sucesso!")

def execute_sql_file(cursor, filename):
    print(f"Executando {filename}...")
    with open(filename, 'r', encoding='utf-8') as f:
        sql_script = f.read()
        cursor.executescript(sql_script)
    print(f"{filename} executado com sucesso!")

def create_sqlite_tables():
    print("Criando tabelas do SQLite...")
    conn = sqlite3.connect('educacional.db')
    cursor = conn.cursor()
    
    # Lista de arquivos SQL para executar
    sql_files = [
        'schema.sql',
        'sql/criar_tabela_simulados.sql',
        'sql/criar_tabela_simulados_professor.sql',
        'sql/criar_tabela_professor_turma.sql'
    ]
    
    for sql_file in sql_files:
        if os.path.exists(sql_file):
            execute_sql_file(cursor, sql_file)
    
    conn.commit()
    conn.close()
    print("Tabelas do SQLite criadas com sucesso!")

if __name__ == '__main__':
    try:
        create_sqlalchemy_tables()
        create_sqlite_tables()
        print("Todas as tabelas foram criadas com sucesso!")
    except Exception as e:
        print(f"Erro ao criar as tabelas: {str(e)}")
