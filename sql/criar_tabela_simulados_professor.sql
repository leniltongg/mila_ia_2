-- Criar tabela de simulados dos professores
CREATE TABLE IF NOT EXISTS simulados_gerados_professor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ano_escolar_id INTEGER NOT NULL,
    mes_id INTEGER NOT NULL,
    disciplina_id INTEGER NOT NULL,
    professor_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'gerado',
    data_criacao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ano_escolar_id) REFERENCES Ano_escolar(id),
    FOREIGN KEY (mes_id) REFERENCES meses(id),
    FOREIGN KEY (disciplina_id) REFERENCES disciplinas(id),
    FOREIGN KEY (professor_id) REFERENCES usuarios(id)
);

-- Criar tabela de questões do simulado
CREATE TABLE IF NOT EXISTS simulado_questoes_professor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    simulado_id INTEGER NOT NULL,
    questao_id INTEGER NOT NULL,
    FOREIGN KEY (simulado_id) REFERENCES simulados_gerados_professor(id),
    FOREIGN KEY (questao_id) REFERENCES banco_questoes(id)
);
