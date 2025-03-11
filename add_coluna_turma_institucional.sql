-- Adiciona a coluna turma_institucional na tabela turmas
ALTER TABLE turmas
ADD COLUMN turma_institucional VARCHAR(50) DEFAULT NULL;
