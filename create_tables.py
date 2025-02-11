from app import app, db
from models import *

with app.app_context():
    print("Criando tabelas do SQLAlchemy...")
    db.create_all()
    print("Tabelas criadas com sucesso!")
