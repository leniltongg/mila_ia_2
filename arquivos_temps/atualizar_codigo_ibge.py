from flask import Flask
from models import db, Escolas

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://mila_user:31952814Gg%40@127.0.0.1/mila_educacional'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def atualizar_codigo_ibge():
    with app.app_context():
        try:
            # Atualiza todas as escolas para terem o código IBGE 2910800
            db.session.query(Escolas).update({Escolas.codigo_ibge: '2910800'})
            db.session.commit()
            print("Código IBGE atualizado com sucesso para todas as escolas!")
        except Exception as e:
            print(f"Erro ao atualizar código IBGE: {e}")
            db.session.rollback()

if __name__ == '__main__':
    atualizar_codigo_ibge()
