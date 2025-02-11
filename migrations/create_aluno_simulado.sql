CREATE TABLE IF NOT EXISTS aluno_simulado (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id INTEGER NOT NULL,
    simulado_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'não respondido',
    data_inicio TIMESTAMP,
    data_fim TIMESTAMP,
    FOREIGN KEY (aluno_id) REFERENCES usuarios (id),
    FOREIGN KEY (simulado_id) REFERENCES simulados_gerados (id)
);
