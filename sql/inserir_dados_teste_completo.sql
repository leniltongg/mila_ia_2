-- Inserir tipo de ensino se não existir
INSERT OR IGNORE INTO tipos_ensino (id, nome) VALUES (1, 'Fundamental');

-- Inserir escola se não existir
INSERT OR IGNORE INTO escolas (
    id, tipo_de_registro, nome_da_escola, codigo_ibge, 
    codigo_inep, cep, endereco, numero, bairro
) VALUES (
    1, '10', 'Escola Teste', '1234567',
    '123456', '12345678', 'Rua Teste', '123', 'Centro'
);

-- Inserir série se não existir
INSERT OR IGNORE INTO Ano_escolar (id, nome) VALUES (1, '6º Ano');

-- Inserir turma se não existir
INSERT OR IGNORE INTO turmas (
    id, tipo_de_registro, codigo_inep, escola_id, 
    tipo_ensino_id, Ano_escolar_id, turma
) VALUES (
    1, '20', '123456', 1, 
    1, 1, '6º Ano A'
);

-- Inserir relacionamento professor-turma usando ID existente (Maria)
INSERT OR IGNORE INTO professor_turma_escola (
    professor_id, turma_id, Ano_escolar_id, escola_id, tipo_ensino_id
) VALUES (18, 1, 1, 1, 1);
