from flask import Flask
from models import db, Usuarios

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://mila_user:31952814Gg%40@127.0.0.1/mila_educacional'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def atualizar_codigo_ibge_alunos():
    with app.app_context():
        try:
            # Atualiza todos os alunos (tipo_usuario_id = 4) para terem o código IBGE 2910800
            db.session.query(Usuarios).filter(
                Usuarios.tipo_usuario_id == 4
            ).update({Usuarios.codigo_ibge: '2910800'})
            
            db.session.commit()
            print("Código IBGE atualizado com sucesso para todos os alunos!")
            
            # Conta quantos alunos foram atualizados
            total_alunos = db.session.query(Usuarios).filter(
                Usuarios.tipo_usuario_id == 4,
                Usuarios.codigo_ibge == '2910800'
            ).count()
            print(f"Total de alunos atualizados: {total_alunos}")
            
        except Exception as e:
            print(f"Erro ao atualizar código IBGE: {e}")
            db.session.rollback()

if __name__ == '__main__':
    atualizar_codigo_ibge_alunos()
