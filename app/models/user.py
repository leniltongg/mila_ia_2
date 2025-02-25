from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from .. import db

class User(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(128))
    tipo_usuario_id = db.Column(db.Integer, nullable=False)
    escola_id = db.Column(db.Integer, db.ForeignKey('escolas.id'))
    Ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'))
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'))
    codigo_ibge = db.Column(db.String(7))
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao_senha = db.Column(db.DateTime)
    ultimo_login = db.Column(db.DateTime)
    tentativas_login = db.Column(db.Integer, default=0)
    bloqueado = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.senha_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.senha_hash, password)

    def is_active(self):
        return not self.bloqueado

class ActivityLog(db.Model):
    __tablename__ = 'activity_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    activity_type = db.Column(db.String(50))
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('activities', lazy=True))
