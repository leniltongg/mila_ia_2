-- Criar tabela de relacionamento entre professor, turma e escola
CREATE TABLE IF NOT EXISTS professor_turma_escola (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    professor_id INTEGER NOT NULL,
    turma_id INTEGER NOT NULL,
    Ano_escolar_id INTEGER NOT NULL,
    escola_id INTEGER NOT NULL,
    tipo_ensino_id INTEGER NOT NULL,
    FOREIGN KEY (professor_id) REFERENCES usuarios(id),
    FOREIGN KEY (turma_id) REFERENCES turmas(id),
    FOREIGN KEY (Ano_escolar_id) REFERENCES Ano_escolar(id),
    FOREIGN KEY (escola_id) REFERENCES escolas(id),
    FOREIGN KEY (tipo_ensino_id) REFERENCES tipos_ensino(id)
);
