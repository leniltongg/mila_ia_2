from flask import Flask
from config import config
from auth import init_login_manager
from routes import conteudo_bp, professores_bp, alunos_bp, simulados_bp

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Inicializa o login manager
    init_login_manager(app)

    # Registra os blueprints
    app.register_blueprint(conteudo_bp)
    app.register_blueprint(professores_bp)
    app.register_blueprint(alunos_bp)
    app.register_blueprint(simulados_bp)

    # Adiciona o filtro chr ao Jinja2
    @app.template_filter('chr')
    def chr_filter(value):
        return chr(value)

    return app
