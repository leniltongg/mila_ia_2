-- Primeiro, criar uma tabela temporária para armazenar os meses em ordem
CREATE TEMPORARY TABLE temp_meses (
    id INT PRIMARY KEY,
    nome VARCHAR(50)
);

-- Inserir os meses na ordem correta
INSERT INTO temp_meses (id, nome) VALUES
(1, 'Janeiro'),
(2, 'Fevereiro'),
(3, 'Março'),
(4, 'Abril'),
(5, 'Maio'),
(6, 'Junho'),
(7, 'Julho'),
(8, 'Agosto'),
(9, 'Setembro'),
(10, 'Outubro'),
(11, 'Novembro'),
(12, 'Dezembro');

-- Atualizar a tabela meses com os IDs corretos
UPDATE meses m
JOIN temp_meses t ON m.nome = t.nome
SET m.id = t.id;

-- Remover a tabela temporária
DROP TEMPORARY TABLE temp_meses;
