-- Inserir relacionamentos de teste entre professor e turmas
INSERT INTO professor_turma_escola (professor_id, turma_id, Ano_escolar_id, escola_id, tipo_ensino_id)
SELECT 
    u.id as professor_id,
    t.id as turma_id,
    t.Ano_escolar_id,
    t.escola_id,
    t.tipo_ensino_id
FROM usuarios u
CROSS JOIN turmas t
WHERE u.tipo_usuario_id = 3  -- Apenas professores
LIMIT 5;  -- Limitar a 5 relacionamentos para teste
