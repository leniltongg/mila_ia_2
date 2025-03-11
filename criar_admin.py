from extensions import db
from models import Usuarios
from flask import Flask
from urllib.parse import quote_plus
from werkzeug.security import generate_password_hash

app = Flask(__name__)

# Configuração do banco de dados
password = quote_plus("31952814Gg@")
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://mila_user:{password}@127.0.0.1/mila_educacional'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def criar_admin():
    """
    Cria um usuário administrador
    """
    with app.app_context():
        # Verificar se o usuário já existe
        usuario_existente = Usuarios.query.filter_by(email='Leniltongg@gmail.com').first()
        
        if usuario_existente:
            print("Usuário já existe!")
            return
            
        # Criar novo usuário administrador
        novo_usuario = Usuarios(
            email='Leniltongg@gmail.com',
            senha=generate_password_hash('123456'),
            nome='Lenilton',
            tipo_usuario_id=1,  # Administrador
            cidade_id=1  # Valor padrão
        )
        
        try:
            db.session.add(novo_usuario)
            db.session.commit()
            print("Usuário administrador criado com sucesso!")
            
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao criar usuário: {e}")

if __name__ == '__main__':
    criar_admin()
