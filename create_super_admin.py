from create_app import create_app
from extensions import db
from models import TiposUsuarios, Usuarios
from werkzeug.security import generate_password_hash

def create_super_admin():
    app = create_app()
    with app.app_context():
        # Verificar se o tipo de usuário 6 (Super Admin) existe
        tipo_admin = db.session.query(TiposUsuarios).filter_by(id=6).first()
        if not tipo_admin:
            tipo_admin = TiposUsuarios(id=6, descricao='Super Administrador')
            db.session.add(tipo_admin)
            db.session.commit()
            print("Tipo de usuário Super Administrador criado com sucesso!")

        # Verificar se o usuário já existe
        admin = db.session.query(Usuarios).filter_by(email='admin@admin.com').first()
        if not admin:
            # Criar usuário super admin
            admin = Usuarios(
                nome='Super Admin',
                email='admin@admin.com',
                senha=generate_password_hash('admin123'),
                tipo_usuario_id=6
            )
            db.session.add(admin)
            db.session.commit()
            print("Usuário Super Admin criado com sucesso!")
            print("Email: admin@admin.com")
            print("Senha: admin123")
        else:
            print("Usuário Super Admin já existe!")

if __name__ == '__main__':
    create_super_admin()
