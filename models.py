from flask_login import UserMixin
from security import hash_password

class User(UserMixin):
    def __init__(self, id, nome, tipo_usuario_id, escola_id, serie_id, turma_id, email, codigo_ibge):
        self.id = id
        self.nome = nome
        self.tipo_usuario_id = tipo_usuario_id
        self.escola_id = escola_id
        self.serie_id = serie_id
        self.turma_id = turma_id
        self.email = email
        self.codigo_ibge = codigo_ibge
        self._password_hash = None

    def get_id(self):
        return str(self.id)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self._password_hash = hash_password(password)

    @property
    def is_admin(self):
        return self.tipo_usuario_id == "Administrador"

    @property
    def is_secretaria(self):
        return self.tipo_usuario_id == "Secretaria Acadêmica"

    def has_role(self, *roles):
        return self.tipo_usuario_id in roles
