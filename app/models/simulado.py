from datetime import datetime
from .. import db

class SimuladosGeradosProfessor(db.Model):
    __tablename__ = 'simulados_gerados_professor'
    
    id = db.Column(db.Integer, primary_key=True)
    professor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    titulo = db.Column(db.String(200))
    descricao = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_envio = db.Column(db.DateTime)
    status = db.Column(db.String(20))

class SimuladoQuestoesProfessor(db.Model):
    __tablename__ = 'simulado_questoes_professor'
    
    id = db.Column(db.Integer, primary_key=True)
    simulado_id = db.Column(db.Integer, db.ForeignKey('simulados_gerados_professor.id'))
    questao_id = db.Column(db.Integer, db.ForeignKey('banco_questoes.id'))
    ordem = db.Column(db.Integer)

class SimuladosEnviados(db.Model):
    __tablename__ = 'simulados_enviados'
    
    id = db.Column(db.Integer, primary_key=True)
    simulado_id = db.Column(db.Integer, db.ForeignKey('simulados_gerados_professor.id'))
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'))
    data_envio = db.Column(db.DateTime, default=datetime.utcnow)
    data_limite = db.Column(db.DateTime)
    status = db.Column(db.String(20))

class AlunoSimulado(db.Model):
    __tablename__ = 'aluno_simulado'
    
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    simulado_id = db.Column(db.Integer, db.ForeignKey('simulados_enviados.id'))
    data_inicio = db.Column(db.DateTime)
    data_conclusao = db.Column(db.DateTime)
    pontuacao = db.Column(db.Float)
    status = db.Column(db.String(20))

class BancoQuestoes(db.Model):
    __tablename__ = 'banco_questoes'
    
    id = db.Column(db.Integer, primary_key=True)
    disciplina_id = db.Column(db.Integer, db.ForeignKey('disciplinas.id'))
    assunto = db.Column(db.String(200))
    nivel = db.Column(db.String(50))
    enunciado = db.Column(db.Text)
    alternativa_a = db.Column(db.Text)
    alternativa_b = db.Column(db.Text)
    alternativa_c = db.Column(db.Text)
    alternativa_d = db.Column(db.Text)
    alternativa_e = db.Column(db.Text)
    resposta_correta = db.Column(db.String(1))
    explicacao = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    fonte = db.Column(db.String(200))
    professor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
