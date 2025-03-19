from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from routes import conteudo_bp, professores_bp, alunos_bp, simulados_bp, admin_v2
from routes.auth import auth_bp
from models import db

app = Flask(__name__)
app.config.from_object('config.Config')

# Inicializa o SQLAlchemy
db.init_app(app)

# Registra os blueprints (apenas uma vez cada)
app.register_blueprint(conteudo_bp)
app.register_blueprint(professores_bp)
app.register_blueprint(alunos_bp)
app.register_blueprint(simulados_bp)
app.register_blueprint(admin_v2, url_prefix='/admin_v2')  # Registra admin_v2 apenas uma vez com url_prefix
app.register_blueprint(auth_bp)

# Configuração do gerenciador de login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

if __name__ == "__main__":
    app.run(debug=True)
