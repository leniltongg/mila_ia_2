BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "alunos" (
	"id"	INTEGER,
	"nome"	TEXT NOT NULL,
	"data_nascimento"	DATE NOT NULL,
	"escola_id"	INTEGER NOT NULL,
	"tipo_ensino"	TEXT NOT NULL,
	"Ano_escolar"	TEXT NOT NULL,
	"turma"	TEXT NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("escola_id") REFERENCES "escolas"("id")
);
CREATE TABLE IF NOT EXISTS "assunto" (
	"id"	INTEGER,
	"disciplina"	TEXT NOT NULL,
	"assunto"	TEXT NOT NULL,
	"professor_id"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("professor_id") REFERENCES "usuarios"("id")
);
CREATE TABLE IF NOT EXISTS "conquistas" (
	"id"	INTEGER,
	"aluno_id"	INTEGER NOT NULL,
	"conquista"	TEXT NOT NULL,
	"pontos_necessarios"	INTEGER NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("aluno_id") REFERENCES "alunos"("id")
);
CREATE TABLE IF NOT EXISTS "disciplinas" (
	"id"	INTEGER,
	"nome"	TEXT NOT NULL UNIQUE,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "escolas" (
	"id"	INTEGER,
	"nome"	TEXT NOT NULL,
	"cep"	TEXT NOT NULL,
	"estado"	TEXT NOT NULL,
	"cidade"	TEXT NOT NULL,
	"bairro"	TEXT NOT NULL,
	"endereco"	TEXT NOT NULL,
	"numero"	TEXT NOT NULL,
	"telefone"	TEXT NOT NULL,
	"cnpj"	TEXT NOT NULL,
	"diretor"	TEXT NOT NULL,
	"tipo_ensino"	TEXT NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "pontuacoes" (
	"id"	INTEGER,
	"aluno_id"	INTEGER NOT NULL,
	"pontos"	INTEGER DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("aluno_id") REFERENCES "alunos"("id")
);
CREATE TABLE IF NOT EXISTS "professores" (
	"id"	INTEGER,
	"nome"	TEXT NOT NULL,
	"email"	TEXT NOT NULL UNIQUE,
	"escola_id"	INTEGER NOT NULL,
	"Ano_escolar"	TEXT NOT NULL,
	"turma"	TEXT NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("escola_id") REFERENCES "escolas"("id")
);
CREATE TABLE IF NOT EXISTS "respostas" (
	"id"	INTEGER,
	"aluno_id"	INTEGER NOT NULL,
	"simulado_id"	INTEGER NOT NULL,
	"pergunta"	TEXT NOT NULL,
	"resposta_dada"	TEXT NOT NULL,
	"correta"	BOOLEAN NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("aluno_id") REFERENCES "alunos"("id"),
	FOREIGN KEY("simulado_id") REFERENCES "simulados"("id")
);
CREATE TABLE IF NOT EXISTS "simulados" (
	"id"	INTEGER,
	"assunto"	TEXT NOT NULL,
	"professor_id"	INTEGER NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("professor_id") REFERENCES "professores"("id")
);
CREATE TABLE IF NOT EXISTS "usuarios" (
	"id"	INTEGER,
	"nome"	TEXT NOT NULL,
	"email"	TEXT NOT NULL UNIQUE,
	"senha"	TEXT NOT NULL,
	"tipo_usuario"	TEXT NOT NULL,
	"escola_id"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("escola_id") REFERENCES "escolas"("id")
);
INSERT INTO "assunto" VALUES (1,'P','Verbos',2);
INSERT INTO "disciplinas" VALUES (1,'Português');
INSERT INTO "disciplinas" VALUES (2,'Matemática');
INSERT INTO "disciplinas" VALUES (3,'Ciências');
INSERT INTO "disciplinas" VALUES (4,'História');
INSERT INTO "disciplinas" VALUES (5,'Geografia');
INSERT INTO "usuarios" VALUES (1,'Administrador','admin@example.com','admin123','Administrador',NULL);
INSERT INTO "usuarios" VALUES (2,'Administrador','leniltongg@gmail.com','123456','Administrador',NULL);
INSERT INTO "usuarios" VALUES (3,'Secretario de educação','secretaria@educacao.com','123456','Secretaria de Educação',NULL);
COMMIT;
