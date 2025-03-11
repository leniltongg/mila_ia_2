-- Renomear coluna CEP na tabela usuarios
ALTER TABLE usuarios
CHANGE COLUMN cep cep_usuario VARCHAR(255);

-- Renomear coluna CEP na tabela escolas
ALTER TABLE escolas
CHANGE COLUMN cep cep_escola VARCHAR(255);
