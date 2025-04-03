from flask import Flask
from extensions import db
from models import TemasRedacao, RedacoesAlunos
import os
from urllib.parse import quote_plus

app = Flask(__name__)

# Configuração do banco de dados
DB_USER = 'mila_user'
DB_PASSWORD = quote_plus('31952814Gg@')
DB_HOST = '127.0.0.1'
DB_NAME = 'mila_educacional'

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa o banco de dados
db.init_app(app)

def create_tables():
    """Create the tables for essays."""
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    create_tables()
    print("Tables created successfully!")
