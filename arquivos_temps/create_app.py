from flask import Flask
from flask_login import LoginManager
from models import db, User
from routes.admin_v2.routes import admin_v2
from routes.auth import auth_bp
from routes.administrador import administrador_bp
from routes import conteudo_bp, professores_bp, alunos_bp, simulados_bp

def create_app():
    app = Flask(__name__)
    
    # Configuração do banco de dados
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///educacional.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'  # Altere para uma chave secreta segura
    
    # Inicialização das extensões
    db.init_app(app)
    
    # Configuração do Login Manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Registro dos blueprints
    app.register_blueprint(conteudo_bp)
    app.register_blueprint(professores_bp)
    app.register_blueprint(alunos_bp)
    app.register_blueprint(simulados_bp)
    app.register_blueprint(admin_v2)
    app.register_blueprint(auth_bp)
    app.register_blueprint(administrador_bp)
    
    return app
