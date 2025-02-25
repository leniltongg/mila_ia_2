from flask import Blueprint

professores_bp = Blueprint('professores', __name__, url_prefix='/professores')

from . import routes  # Importar as rotas depois de criar o blueprint
