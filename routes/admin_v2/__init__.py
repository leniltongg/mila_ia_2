from flask import Blueprint

admin_v2 = Blueprint('admin_v2', __name__)

from . import routes
