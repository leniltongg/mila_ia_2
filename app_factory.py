from flask import Flask
from flask_login import LoginManager
from models import db, User
from routes import conteudo_bp, alunos_bp, simulados_bp, admin_v2
from routes.auth import auth_bp
from routes.professores_bp import professores_bp

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # Configurar o upload folder
    app.config['UPLOAD_FOLDER'] = 'uploads'
    
    # Inicializar o SQLAlchemy
    db.init_app(app)
    
    # Registrar blueprints
    app.register_blueprint(conteudo_bp)
    app.register_blueprint(professores_bp)
    app.register_blueprint(alunos_bp)
    app.register_blueprint(simulados_bp)
    app.register_blueprint(admin_v2)
    app.register_blueprint(auth_bp)
    
    # Configurar o Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    return app
