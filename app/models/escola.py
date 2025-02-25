from .. import db

class Escola(db.Model):
    __tablename__ = 'escolas'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    codigo_ibge = db.Column(db.String(7))
    endereco = db.Column(db.String(200))
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    diretor = db.Column(db.String(100))

class Ano_escolar(db.Model):
    __tablename__ = 'Ano_escolar'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    tipo_ensino_id = db.Column(db.Integer, db.ForeignKey('tipos_ensino.id'))

class Turma(db.Model):
    __tablename__ = 'turmas'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    Ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'))
    escola_id = db.Column(db.Integer, db.ForeignKey('escolas.id'))
    turno = db.Column(db.String(20))

class TipoEnsino(db.Model):
    __tablename__ = 'tipos_ensino'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    descricao = db.Column(db.String(200))

class Disciplina(db.Model):
    __tablename__ = 'disciplinas'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    descricao = db.Column(db.String(200))
    Ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'))
