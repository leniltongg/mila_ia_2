-- Atualizar tabela de simulados
DROP TABLE IF EXISTS simulados;
CREATE TABLE simulados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    data_aplicacao DATE NOT NULL,
    serie_id INTEGER NOT NULL,
    disciplina_id INTEGER NOT NULL,
    shuffle_questoes BOOLEAN NOT NULL DEFAULT 1,
    shuffle_alternativas BOOLEAN NOT NULL DEFAULT 1,
    criador_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'rascunho',
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_publicacao TIMESTAMP,
    FOREIGN KEY (serie_id) REFERENCES series(id),
    FOREIGN KEY (disciplina_id) REFERENCES disciplinas(id),
    FOREIGN KEY (criador_id) REFERENCES usuarios(id)
);

-- Atualizar tabela de questões
DROP TABLE IF EXISTS questoes;
CREATE TABLE questoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    enunciado TEXT NOT NULL,
    alternativa_a TEXT NOT NULL,
    alternativa_b TEXT NOT NULL,
    alternativa_c TEXT NOT NULL,
    alternativa_d TEXT NOT NULL,
    alternativa_e TEXT NOT NULL,
    alternativa_correta CHAR(1) NOT NULL,
    explicacao TEXT,
    nivel TEXT NOT NULL DEFAULT 'Médio',
    serie_id INTEGER NOT NULL,
    disciplina_id INTEGER NOT NULL,
    criador_id INTEGER NOT NULL,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (serie_id) REFERENCES series(id),
    FOREIGN KEY (disciplina_id) REFERENCES disciplinas(id),
    FOREIGN KEY (criador_id) REFERENCES usuarios(id),
    CHECK (alternativa_correta IN ('A', 'B', 'C', 'D', 'E')),
    CHECK (nivel IN ('Fácil', 'Médio', 'Difícil'))
);

-- Atualizar tabela de questões do simulado
DROP TABLE IF EXISTS simulado_questoes;
CREATE TABLE simulado_questoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    simulado_id INTEGER NOT NULL,
    questao_id INTEGER NOT NULL,
    ordem INTEGER NOT NULL,
    FOREIGN KEY (simulado_id) REFERENCES simulados(id),
    FOREIGN KEY (questao_id) REFERENCES questoes(id)
);

-- Criar índices para melhor performance
CREATE INDEX idx_questoes_serie_disciplina ON questoes(serie_id, disciplina_id);
CREATE INDEX idx_simulados_criador ON simulados(criador_id);
CREATE INDEX idx_simulado_questoes_simulado ON simulado_questoes(simulado_id);
