# Importar os blueprints
from .conteudo import conteudo_bp
from .professores.routes import professores_bp
from .alunos_bp import alunos_bp
from .simulados import simulados_bp
from .secretaria_educacao import bp as secretaria_educacao_bp

# Exportar os blueprints
__all__ = [
    'conteudo_bp',
    'professores_bp',
    'alunos_bp',
    'simulados_bp',
    'secretaria_educacao_bp'
]