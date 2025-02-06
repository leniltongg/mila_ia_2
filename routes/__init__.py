from flask import Blueprint

# Importar as rotas
from . import conteudo
from . import professores
from . import alunos_bp
from . import simulados

# Exportar os blueprints
from .conteudo import conteudo_bp
from .professores import professores_bp
from .alunos_bp import alunos_bp
from .simulados import simulados_bp

__all__ = ['conteudo_bp', 'professores_bp', 'alunos_bp', 'simulados_bp']