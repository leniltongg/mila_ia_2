-- Adicionar coluna turma_institucional na tabela usuarios
ALTER TABLE usuarios
ADD COLUMN turma_institucional VARCHAR(255);
