# Continuação dos modelos
class EscolaTiposEnsino(db.Model):
    __tablename__ = 'escola_tipos_ensino'
    id = db.Column(db.Integer, primary_key=True)
    escola_id = db.Column(db.Integer, db.ForeignKey('escolas.id'), nullable=False)
    tipo_ensino_id = db.Column(db.Integer, db.ForeignKey('tipos_ensino.id'), nullable=False)

class ProfessorTurmaEscola(db.Model):
    __tablename__ = 'professor_turma_escola'
    id = db.Column(db.Integer, primary_key=True)
    professor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    escola_id = db.Column(db.Integer, db.ForeignKey('escolas.id'), nullable=False)
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=False)
    tipo_ensino_id = db.Column(db.Integer, db.ForeignKey('tipos_ensino.id'), nullable=False)
    ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'), nullable=False)

class Assuntos(db.Model):
    __tablename__ = 'assuntos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    disciplina_id = db.Column(db.Integer, db.ForeignKey('disciplinas.id'), nullable=False)
    ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('nome', 'disciplina_id', 'ano_escolar_id', 'professor_id'),)

class BancoQuestoes(db.Model):
    __tablename__ = 'banco_questoes'
    id = db.Column(db.Integer, primary_key=True)
    questao = db.Column(db.Text, nullable=False)
    alternativa_a = db.Column(db.Text, nullable=False)
    alternativa_b = db.Column(db.Text, nullable=False)
    alternativa_c = db.Column(db.Text, nullable=False)
    alternativa_d = db.Column(db.Text, nullable=False)
    alternativa_e = db.Column(db.Text, nullable=True)
    questao_correta = db.Column(db.String(1), nullable=False)
    disciplina_id = db.Column(db.Integer, db.ForeignKey('disciplinas.id'), nullable=False)
    assunto = db.Column(db.Text, nullable=False)
    ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'), nullable=True)
    mes_id = db.Column(db.Integer, db.ForeignKey('meses.id'), nullable=True)
    data_criacao = db.Column(db.DateTime, nullable=True, default=db.func.current_timestamp())

class SimuladosGerados(db.Model):
    __tablename__ = 'simulados_gerados'
    id = db.Column(db.Integer, primary_key=True)
    ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'), nullable=False)
    mes_id = db.Column(db.Integer, db.ForeignKey('meses.id'), nullable=False)
    status = db.Column(db.String(20), nullable=True, default='gerado')
    data_envio = db.Column(db.DateTime, nullable=True, default=db.func.current_timestamp())
    disciplina_id = db.Column(db.Integer, db.ForeignKey('disciplinas.id'), nullable=True)

class SimuladosGeradosProfessor(db.Model):
    __tablename__ = 'simulados_gerados_professor'
    id = db.Column(db.Integer, primary_key=True)
    professor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    disciplina_id = db.Column(db.Integer, db.ForeignKey('disciplinas.id'), nullable=False)
    ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'), nullable=False)
    data_criacao = db.Column(db.DateTime, nullable=True, default=db.func.current_timestamp())
    mes_id = db.Column(db.Integer, db.ForeignKey('meses.id'), nullable=True)
    status = db.Column(db.String(20), nullable=True, default='gerado')

class SimuladoQuestoes(db.Model):
    __tablename__ = 'simulado_questoes'
    id = db.Column(db.Integer, primary_key=True)
    simulado_id = db.Column(db.Integer, db.ForeignKey('simulados_gerados.id'), nullable=False)
    questao_id = db.Column(db.Integer, db.ForeignKey('banco_questoes.id'), nullable=True)

class SimuladoQuestoesProfessor(db.Model):
    __tablename__ = 'simulado_questoes_professor'
    id = db.Column(db.Integer, primary_key=True)
    simulado_id = db.Column(db.Integer, db.ForeignKey('simulados_gerados_professor.id'), nullable=False)
    questao_id = db.Column(db.Integer, db.ForeignKey('banco_questoes.id'), nullable=False)

class SimuladosEnviados(db.Model):
    __tablename__ = 'simulados_enviados'
    id = db.Column(db.Integer, primary_key=True)
    simulado_id = db.Column(db.Integer, db.ForeignKey('simulados_gerados_professor.id'), nullable=False)
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=False)
    data_envio = db.Column(db.DateTime, nullable=True, default=db.func.current_timestamp())
    status = db.Column(db.String(20), nullable=True, default='enviado')
    data_limite = db.Column(db.DateTime, nullable=True)

class AlunoSimulado(db.Model):
    __tablename__ = 'aluno_simulado'
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    simulado_id = db.Column(db.Integer, db.ForeignKey('simulados_enviados.id'), nullable=False)
    status = db.Column(db.String(20), nullable=True, default='não respondido')
    data_resposta = db.Column(db.DateTime, nullable=True)

class DesempenhoSimulado(db.Model):
    __tablename__ = 'desempenho_simulado'
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    simulado_id = db.Column(db.Integer, db.ForeignKey('simulados_enviados.id'), nullable=False)
    escola_id = db.Column(db.Integer, db.ForeignKey('escolas.id'), nullable=False)
    ano_escolar_id = db.Column(db.Integer, db.ForeignKey('Ano_escolar.id'), nullable=False)
    codigo_ibge = db.Column(db.Integer, nullable=False)
    respostas_aluno = db.Column(db.JSON, nullable=False)
    respostas_corretas = db.Column(db.JSON, nullable=False)
    desempenho = db.Column(db.Numeric(5, 2), nullable=False)
    data_resposta = db.Column(db.DateTime, nullable=True, default=db.func.current_timestamp())
    tipo_usuario_id = db.Column(db.Integer, nullable=False, default=5)
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=True)
