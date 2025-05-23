CREATE TABLE IF NOT EXISTS "banco_questoes" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    questao TEXT NOT NULL,
    alternativa_a TEXT NOT NULL,
    alternativa_b TEXT NOT NULL,
    alternativa_c TEXT NOT NULL,
    alternativa_d TEXT NOT NULL,
    alternativa_e TEXT,
    questao_correta TEXT NOT NULL,
    disciplina_id INTEGER NOT NULL,
    assunto TEXT NOT NULL,
    ano_escolar_id INTEGER,
    mes_id INTEGER,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (disciplina_id) REFERENCES disciplinas (id)
);
