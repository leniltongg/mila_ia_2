-- Tabela para armazenar questões do banco de questões
CREATE TABLE IF NOT EXISTS questoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    professor_id INTEGER NOT NULL,
    disciplina TEXT NOT NULL,
    assunto TEXT NOT NULL,
    nivel TEXT NOT NULL,
    tipo TEXT NOT NULL,
    enunciado TEXT NOT NULL,
    alternativas TEXT,  -- JSON com alternativas (para questões objetivas)
    resposta_correta TEXT NOT NULL,
    explicacao TEXT,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (professor_id) REFERENCES user(id)
);

-- Tabela para armazenar simulados
CREATE TABLE IF NOT EXISTS simulados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    professor_id INTEGER NOT NULL,
    titulo TEXT NOT NULL,
    descricao TEXT,
    disciplina TEXT NOT NULL,
    duracao INTEGER NOT NULL,  -- em minutos
    data_inicio TIMESTAMP NOT NULL,
    data_fim TIMESTAMP NOT NULL,
    status TEXT DEFAULT 'rascunho',  -- rascunho, publicado, encerrado
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (professor_id) REFERENCES user(id)
);

-- Tabela para relacionar questões aos simulados
CREATE TABLE IF NOT EXISTS simulado_questoes (
    simulado_id INTEGER NOT NULL,
    questao_id INTEGER NOT NULL,
    ordem INTEGER NOT NULL,
    pontos REAL NOT NULL DEFAULT 1.0,
    PRIMARY KEY (simulado_id, questao_id),
    FOREIGN KEY (simulado_id) REFERENCES simulados(id),
    FOREIGN KEY (questao_id) REFERENCES questoes(id)
);

-- Tabela para armazenar respostas dos alunos
CREATE TABLE IF NOT EXISTS respostas_simulado (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id INTEGER NOT NULL,
    simulado_id INTEGER NOT NULL,
    questao_id INTEGER NOT NULL,
    resposta TEXT NOT NULL,
    correta BOOLEAN,
    pontos REAL,
    tempo_resposta INTEGER,  -- em segundos
    data_resposta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (aluno_id) REFERENCES user(id),
    FOREIGN KEY (simulado_id) REFERENCES simulados(id),
    FOREIGN KEY (questao_id) REFERENCES questoes(id)
);

-- Tabela para armazenar resultados dos simulados
CREATE TABLE IF NOT EXISTS resultados_simulado (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id INTEGER NOT NULL,
    simulado_id INTEGER NOT NULL,
    pontuacao_total REAL NOT NULL,
    tempo_total INTEGER NOT NULL,  -- em segundos
    data_inicio TIMESTAMP NOT NULL,
    data_fim TIMESTAMP NOT NULL,
    status TEXT DEFAULT 'em_andamento',  -- em_andamento, finalizado
    FOREIGN KEY (aluno_id) REFERENCES user(id),
    FOREIGN KEY (simulado_id) REFERENCES simulados(id)
);
