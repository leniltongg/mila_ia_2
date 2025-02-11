from app import app, db
from models import User, TIPO_USUARIO_ADMIN

def criar_admin():
    with app.app_context():
        # Verifica se já existe um admin
        admin = User.query.filter_by(tipo_usuario_id=TIPO_USUARIO_ADMIN).first()
        if not admin:
            # Cria um novo usuário admin
            admin = User(
                nome='Administrador',
                email='admin@admin.com',
                tipo_usuario_id=TIPO_USUARIO_ADMIN
            )
            admin.senha = 'admin123'  # A senha será hasheada automaticamente pelo modelo
            
            db.session.add(admin)
            db.session.commit()
            print("Usuário administrador criado com sucesso!")
            print("Email: admin@admin.com")
            print("Senha: admin123")
        else:
            print("Já existe um usuário administrador!")
            print(f"Email: {admin.email}")

if __name__ == '__main__':
    criar_admin()
