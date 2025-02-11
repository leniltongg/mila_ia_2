-- Criar tabela de simulados para alunos
CREATE TABLE IF NOT EXISTS simulados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    simulado_professor_id INTEGER NOT NULL,
    turma_id INTEGER NOT NULL,
    data_limite DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'disponivel',  -- disponivel, em_andamento, finalizado
    data_criacao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (simulado_professor_id) REFERENCES simulados_gerados_professor(id),
    FOREIGN KEY (turma_id) REFERENCES turmas(id)
);

-- Criar tabela de questões do simulado
CREATE TABLE IF NOT EXISTS simulado_questoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    simulado_id INTEGER NOT NULL,
    questao_id INTEGER NOT NULL,
    FOREIGN KEY (simulado_id) REFERENCES simulados(id),
    FOREIGN KEY (questao_id) REFERENCES banco_questoes(id)
);

-- Criar tabela de respostas dos alunos
CREATE TABLE IF NOT EXISTS simulado_respostas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    simulado_id INTEGER NOT NULL,
    aluno_id INTEGER NOT NULL,
    questao_id INTEGER NOT NULL,
    resposta TEXT NOT NULL,  -- A, B, C, D ou E
    data_resposta DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (simulado_id) REFERENCES simulados(id),
    FOREIGN KEY (aluno_id) REFERENCES usuarios(id),
    FOREIGN KEY (questao_id) REFERENCES banco_questoes(id)
);
