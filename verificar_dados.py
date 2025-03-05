from extensions import db
from models import Usuarios, Escolas
from flask import Flask
from urllib.parse import quote_plus

app = Flask(__name__)
password = quote_plus('31952814Gg@')
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://mila_user:{password}@127.0.0.1/mila_educacional'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def verificar_dados():
    with app.app_context():
        # Verificar range de IDs
        menor_id = db.session.query(db.func.min(Usuarios.id)).scalar()
        maior_id = db.session.query(db.func.max(Usuarios.id)).scalar()
        print(f"\nRange de IDs no banco:")
        print(f"Menor ID: {menor_id}")
        print(f"Maior ID: {maior_id}")
        
        # Mostrar alguns usuários recentes
        print("\nÚltimos 5 usuários cadastrados:")
        print("==============================")
        
        usuarios = db.session.query(Usuarios).order_by(Usuarios.id.desc()).limit(5).all()
        for u in usuarios:
            print(f"\nID: {u.id}")
            print(f"Nome: {u.nome}")
            print(f"CPF: {u.cpf}")
            print(f"Data Nascimento: {u.data_nascimento}")
            print(f"Mãe: {u.mae}")
            print(f"Pai: {u.pai}")
            print(f"Escola ID: {u.escola_id}")
            
        # Estatísticas gerais
        print("\nEstatísticas Gerais:")
        print("===================")
        
        total_usuarios = db.session.query(Usuarios).count()
        print(f"\nTotal de usuários: {total_usuarios}")
        
        usuarios_com_cpf = db.session.query(Usuarios).filter(Usuarios.cpf.isnot(None)).count()
        print(f"Usuários com CPF: {usuarios_com_cpf}")
        
        usuarios_com_data_nasc = db.session.query(Usuarios).filter(Usuarios.data_nascimento.isnot(None)).count()
        print(f"Usuários com Data de Nascimento: {usuarios_com_data_nasc}")
        
        usuarios_com_mae = db.session.query(Usuarios).filter(Usuarios.mae.isnot(None)).count()
        print(f"Usuários com Nome da Mãe: {usuarios_com_mae}")
        
        usuarios_com_pai = db.session.query(Usuarios).filter(Usuarios.pai.isnot(None)).count()
        print(f"Usuários com Nome do Pai: {usuarios_com_pai}")
        
        usuarios_com_sexo = db.session.query(Usuarios).filter(Usuarios.sexo.isnot(None)).count()
        print(f"Usuários com Sexo: {usuarios_com_sexo}")

if __name__ == '__main__':
    verificar_dados()
